# -*- coding: utf-8 -*-
# This file is part of overlayfs plugin for mock
# Copyright (C) 2018  Zdeněk Žamberský ( https://github.com/zzambers )
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import overlayfs
import os
import os.path
import sys

#######################
#	 Dummy classes	  #
#######################

# ( to satisfy plugin's constructor... )

class DummyPlugins(object):

	def add_hook(self, name, method):
		return

class DummyConf(object):

	def __init__(self, base_dir):
		self.base_dir = base_dir

	def get(self, name):
		if name == "base_dir":
			return self.base_dir

class DummyBuildRoot(object):

	def __init__(self, rootDir, sharedRootName):
		self.rootdir = rootDir
		self.shared_root_name = sharedRootName

####################
#	 TEST class	   #
####################

class LayersTest(object):

	def __init__(self, baseDir, rootDir, configName):
		plugins = DummyPlugins()
		conf = DummyConf(baseDir)
		buildRoot = DummyBuildRoot(rootDir, configName)
		self.plugin = overlayfs.OverlayFsPlugin(plugins, conf, buildRoot)

	# assert methods used by test method

	def assertTrue(self, value):
		if not value:
			raise Exception("Assertion error: true expected !")

	def assertFileExists(self, fileName):
		if not os.path.exists(fileName):
			errorString = "Assertion error: file does not exist: " + fileName + " !"
			raise Exception(errorString)

	def assertFileHasContent(self, fileName, expected):
		self.assertFileExists(fileName)
		value = self.plugin.readFile(fileName)
		if not value == expected:
			errorString = "Assertion error: file " + fileName + " expeceted content: " + expected + " actual content: " + value
			raise Exception(errorString)

	def assertLayerRefcount(self, name, ntimes):
		layerId = self.plugin.getLayerFromRef(name)
		self.assertFileHasContent(self.plugin.getLayerRefCounterFile(layerId), str(ntimes))

	def assertSameLayer(self, name1, name2):
		layer1Id = self.plugin.getLayerFromRef(name1)
		layer2Id = self.plugin.getLayerFromRef(name2)
		if not self.plugin.isSameLayer(layer1Id, layer2Id):
			errorString = "Assertion error: " + name1 + " and " + name2 + " do not point to the same layer!"
			raise Exception(errorString)

	def assertNotSameLayer(self, name1, name2):
		layer1Id = self.plugin.getLayerFromRef(name1)
		layer2Id = self.plugin.getLayerFromRef(name2)
		if self.plugin.isSameLayer(layer1Id, layer2Id):
			errorString = "Assertion error: " + name1 + " and " + name2 + " do point to the same layer!"
			raise Exception(errorString)

	def assertRefExists(self, name):
		if not self.plugin.refExists(name):
			errorString = "Assertion error: ref " + name + " does not exist!"
			raise Exception(errorString)

	def assertRefNotExist(self, name):
		if self.plugin.refExists(name):
			errorString = "Assertion error: ref " + name + " exists!"
			raise Exception(errorString)

	def assertNLayers(self, expected):
		n = len(os.listdir(self.plugin.getLayersDir()))
		if not n == expected:
			errorString = "Assertion error: expected " + str(expected) + " layers, but got " + str(n) + " layers !"
			raise Exception(errorString)

	# tests that layers, refs work correctly, but does not actually mount
	# anything
	def runTest(self):
		plugin = self.plugin

		plugin.basicInit()

		pluginBaseDir = plugin.getPluginInstanceDir()
		layersDir = plugin.getLayersDir()
		refsDir = plugin.getRefsDir()
		self.assertFileExists(pluginBaseDir)
		self.assertFileExists(layersDir)
		self.assertFileExists(refsDir)

		plugin.initLayers()
		baseLayerRef = plugin.getBaseLayerRef()
		upperLayerRef = plugin.getUpperLayerRef()
		currentLayerRef = plugin.getCurrentLayerRef()
		self.assertRefExists(baseLayerRef)
		self.assertRefExists(upperLayerRef)
		self.assertRefExists(currentLayerRef)

		self.assertNLayers(1)
		# .base == .upper
		self.assertSameLayer(baseLayerRef, upperLayerRef)
		# .base == .current
		self.assertSameLayer(baseLayerRef, currentLayerRef)
		# refs: .base, .upper, .current
		self.assertLayerRefcount(baseLayerRef, 3)

		plugin.prepareLayersForMount()
		self.assertNLayers(2)
		# .base != .upper
		self.assertNotSameLayer(baseLayerRef, upperLayerRef)
		# .base == .current
		self.assertSameLayer(baseLayerRef, currentLayerRef)
		# refs: .base, .current + 1 layer
		self.assertLayerRefcount(baseLayerRef, 3)
		# refs: .upper
		self.assertLayerRefcount(upperLayerRef, 1)

		layerARef = "a"
		self.plugin.createSnapshot(layerARef)
		self.assertNLayers(2)
		# a == .upper
		self.assertSameLayer(layerARef, upperLayerRef)
		# a == .current
		self.assertSameLayer(layerARef, currentLayerRef)
		# refs: .base + 1 layer
		self.assertLayerRefcount(baseLayerRef, 2)
		# refs: a, .upper, .current
		self.assertLayerRefcount(layerARef, 3)

		plugin.prepareLayersForMount()
		self.assertNLayers(3)
		# a != .upper
		self.assertNotSameLayer(layerARef, upperLayerRef)
		# a == .current
		self.assertSameLayer(layerARef, currentLayerRef)
		# refs: .base + 1 layer
		self.assertLayerRefcount(baseLayerRef, 2)
		# refs: a, .current + 1 layer
		self.assertLayerRefcount(layerARef, 3)
		# refs: .upper
		self.assertLayerRefcount(upperLayerRef, 1)

		plugin.restoreSnapshot(layerARef)
		self.assertNLayers(2)
		# a == .upper
		self.assertSameLayer(layerARef, upperLayerRef)
		# a == .current
		self.assertSameLayer(layerARef, currentLayerRef)
		# refs: base + 1 layer
		self.assertLayerRefcount(baseLayerRef, 2)
		# refs: a, .current, .upper
		self.assertLayerRefcount(layerARef, 3)

		plugin.prepareLayersForMount()
		self.assertNLayers(3)
		# a != .upper
		self.assertNotSameLayer(layerARef, upperLayerRef)
		# a == .current
		self.assertSameLayer(layerARef, currentLayerRef)
		# refs: base + 1 layer
		self.assertLayerRefcount(baseLayerRef, 2)
		# refs: a, .current + 1 layer
		self.assertLayerRefcount(layerARef, 3)
		# refs: .upper
		self.assertLayerRefcount(upperLayerRef, 1)

		layerBRef = "b"
		plugin.createSnapshot(layerBRef)
		self.assertNLayers(3)
		# b == .upper
		self.assertSameLayer(layerBRef, upperLayerRef)
		# b == .current
		self.assertSameLayer(layerBRef, currentLayerRef)
		# refs: base + 1 layer
		self.assertLayerRefcount(baseLayerRef, 2)
		# refs: a, + 1 layer
		self.assertLayerRefcount(layerARef, 2)
		# refs: b, .current, .upper
		self.assertLayerRefcount(layerBRef, 3)

		plugin.prepareLayersForMount()
		plugin.prepareLayersForMount()
		self.assertNLayers(4)
		# a != .upper
		self.assertNotSameLayer(layerARef, upperLayerRef)
		# b != .upper
		self.assertNotSameLayer(layerBRef, upperLayerRef)
		# b == .current
		self.assertSameLayer(layerBRef, currentLayerRef)
		# refs: .base + 1 layer
		self.assertLayerRefcount(baseLayerRef, 2)
		# refs: a, + 1 layer
		self.assertLayerRefcount(layerARef, 2)
		# refs: b, .current + 1 layer
		self.assertLayerRefcount(layerBRef, 3)

		plugin.restoreSnapshot(baseLayerRef)
		self.assertNLayers(3)
		# a != .upper
		self.assertNotSameLayer(layerARef, upperLayerRef)
		# b != .upper
		self.assertNotSameLayer(layerBRef, upperLayerRef)
		# .base == .upper
		self.assertSameLayer(baseLayerRef, upperLayerRef)
		# .base == .current
		self.assertSameLayer(baseLayerRef, currentLayerRef)
		# refs: .base, .upper .current + 1 layer
		self.assertLayerRefcount(baseLayerRef, 4)
		# refs: a, + 1 layer
		self.assertLayerRefcount(layerARef, 2)
		# refs: b
		self.assertLayerRefcount(layerBRef, 1)

		plugin.deleteSnapshot(layerARef)
		self.assertNLayers(3)
		self.assertRefNotExist(layerARef)
		# b != .upper
		self.assertNotSameLayer(layerBRef, upperLayerRef)
		# .base == .upper
		self.assertSameLayer(baseLayerRef, upperLayerRef)
		# .base == .current
		self.assertSameLayer(baseLayerRef, currentLayerRef)
		# refs: .base, .upper, .current + 1 layer
		self.assertLayerRefcount(baseLayerRef, 4)
		# refs: b
		self.assertLayerRefcount(layerBRef, 1)

		plugin.deleteSnapshot(layerBRef)
		self.assertNLayers(1)
		self.assertRefNotExist(layerBRef)
		self.assertSameLayer(baseLayerRef, upperLayerRef)
		# refs: base, .upper, .current
		self.assertLayerRefcount(baseLayerRef, 3)


def main():
	args = sys.argv
	if len(args) == 2:
		currentDir = args[1]
	else:
		currentDir = os.getcwd()

	baseDir = os.path.join(currentDir, "overlayfs-base")
	rootDir = os.path.join(currentDir, "root")
	configName = "config-name"

	test = LayersTest(baseDir, rootDir, configName)
	test.runTest()


if __name__ == "__main__":
	main()
