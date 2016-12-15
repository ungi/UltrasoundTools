import os
import vtk, qt, ctk, slicer
import math
import numpy as np
from slicer.ScriptedLoadableModule import *
import logging


#
# SkullMarker
#

class SkullMarker(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "SkullMarker" # TODO make this more human readable by adding spaces
    self.parent.categories = ["Ultrasound"]
    self.parent.dependencies = []
    self.parent.contributors = ["Tamas Ungi (Perk Lab)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This module creates fiducial points on skull surfaces as scanned using ultrasound.
    """
    self.parent.acknowledgementText = """
    Perk Lab
""" # replace with organization, grant and thanks.

#
# SkullMarkerWidget
#

class SkullMarkerWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.logic = SkullMarkerLogic()


  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Inputs Area
    #
    inputsCollapsibleButton = ctk.ctkCollapsibleButton()
    inputsCollapsibleButton.text = "Inputs"
    self.layout.addWidget(inputsCollapsibleButton)

    # Layout within the dummy collapsible button
    inputsFormLayout = qt.QFormLayout(inputsCollapsibleButton)

    #
    # input volume selector
    #
    self.inputSelector = slicer.qMRMLNodeComboBox()
    self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    self.inputSelector.selectNodeUponCreation = True
    self.inputSelector.addEnabled = False
    self.inputSelector.removeEnabled = False
    self.inputSelector.noneEnabled = False
    self.inputSelector.showHidden = False
    self.inputSelector.showChildNodeTypes = False
    self.inputSelector.setMRMLScene(slicer.mrmlScene)
    self.inputSelector.setToolTip("Pick the input to the algorithm.")
    inputsFormLayout.addRow("Input Volume: ", self.inputSelector)

    #
    # PLUS configuration file selector
    #
    fileLayout = qt.QHBoxLayout()
    self.configFile = qt.QLineEdit()
    self.configFile.setReadOnly(True)
    self.configFileButton = qt.QPushButton()
    self.configFileButton.setText("Select File")
    fileLayout.addWidget(self.configFile)
    fileLayout.addWidget(self.configFileButton)
    inputsFormLayout.addRow("Configuration file: ", fileLayout)

    #
    # Fiducial node selector
    #
    self.fiducialSelector = slicer.qMRMLNodeComboBox()
    self.fiducialSelector.nodeTypes = (("vtkMRMLMarkupsFiducialNode"), "")
    self.fiducialSelector.addEnabled = True
    self.fiducialSelector.removeEnabled = True
    self.fiducialSelector.renameEnabled = True
    self.fiducialSelector.setMRMLScene(slicer.mrmlScene)
    self.fiducialSelector.setToolTip(
      "Select the fiducial list which will contain fiducials marking bone surfaces along scanlines")
    inputsFormLayout.addRow("Fiducials points: ", self.fiducialSelector)

    #
    # Number of scanlines selector
    #
    self.scanlineNumber = qt.QSpinBox()
    self.scanlineNumber.setMinimum(1)
    self.scanlineNumber.setSingleStep(1)
    inputsFormLayout.addRow("Number of scanlines: ", self.scanlineNumber)

    #
    # Minimum Distance between points
    #
    self.minimumDistanceBetweenPointsMM = qt.QSpinBox()
    self.minimumDistanceBetweenPointsMM.setMinimum(2)
    self.minimumDistanceBetweenPointsMM.setSingleStep(1)
    self.minimumDistanceBetweenPointsMM.setSuffix(" mm")
    inputsFormLayout.addRow("Minimum distance between points: ", self.minimumDistanceBetweenPointsMM)

    #
    # Starting depth for fiducial placement
    #
    self.startingDepthMM = qt.QSpinBox()
    self.startingDepthMM.setMinimum(2)  # Bone not before 2mm
    self.startingDepthMM.setSingleStep(1)
    self.startingDepthMM.setSuffix(" mm")
    inputsFormLayout.addRow("Starting fiducial depth: ", self.startingDepthMM)

    #
    # Ending depth for fiducial placement
    #
    self.endingDepthMM = qt.QSpinBox()
    self.endingDepthMM.setMinimum(2)
    self.endingDepthMM.setSingleStep(1)
    self.endingDepthMM.setValue(10)
    self.endingDepthMM.setSuffix(" mm")
    inputsFormLayout.addRow("Ending fiducial depth: ", self.endingDepthMM)

    #
    # Threshold slider
    #
    self.thresholdSlider = ctk.ctkSliderWidget()
    self.thresholdSlider.maximum = 255
    self.thresholdSlider.setDecimals(0)
    self.thresholdSlider.setValue(200)
    inputsFormLayout.addRow("Bone surface threshold: ", self.thresholdSlider)

    #
    # Inputs Area
    #
    functionsCollapsibleButton = ctk.ctkCollapsibleButton()
    functionsCollapsibleButton.text = "Functions"
    self.layout.addWidget(functionsCollapsibleButton)

    # Layout within the dummy collapsible button
    functionsFormLayout = qt.QFormLayout(functionsCollapsibleButton)

    #
    # Configure parameters button
    #
    self.configureParametersButton = qt.QPushButton("Begin configuring threshold")
    self.configureParametersButton.setStyleSheet('QPushButton {background-color: #e67300}')
    self.configureParametersButton.toolTip = "Enables threshold configuration by placing fiducials to see current results, but does not save them"
    # self.configureParametersButton.enabled = False
    functionsFormLayout.addRow(self.configureParametersButton)

    #
    # Start fiducial placement button
    #
    self.fiducialPlacementButton = qt.QPushButton("Start fiducial placement")
    self.fiducialPlacementButton.setCheckable(True)
    self.fiducialPlacementButton.toolTip = "Starts and stops fiducial placement on bone surfaces along scanlines."
    # self.fiducialPlacementButton.setStyleSheet('QPushButton {background-color: #009900}')
    # self.fiducialPlacementButton.enabled = False
    functionsFormLayout.addRow(self.fiducialPlacementButton)

    self.messageLabel = qt.QLabel()
    functionsFormLayout.addRow(self.messageLabel)


    # connections
    self.fiducialPlacementButton.connect('clicked(bool)', self.onFiducialPlacementButton)
    self.configureParametersButton.connect('clicked(bool)', self.onConfigureParametersButton)
    self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputSelect)
    self.fiducialSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInputSelect)
    self.configFileButton.connect('clicked(bool)', self.selectFile)
    self.startingDepthMM.connect('valueChanged(int)', self.validateStartingDepth)
    self.endingDepthMM.connect('valueChanged(int)', self.validateEndingDepth)
    self.thresholdSlider.connect('valueChanged(double)', self.setThreshold)
    self.minimumDistanceBetweenPointsMM.connect('valueChanged(double)', self.validateMinimumDistance)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.onInputSelect()

  def cleanup(self):
    pass


  def onInputSelect(self):
    self.updateGui()


  def selectFile(self):
    fileName = qt.QFileDialog().getOpenFileName()
    self.configFile.setText(fileName)
    self.updateGui()


  def onFiducialPlacementButton(self):

    if self.fiducialPlacementButton.isChecked() == False:
      self.logic.stopTrackingVolumeChanges(self.inputSelector.currentNode())
      self.fiducialPlacementButton.setText("Start fiducial placement")
      self.messageLabel.setText('')
      return

    if len(self.configFile.text) < 4:
      self.messageLabel.setText('Select configuration file!')
      self.fiducialPlacementButton.setChecked(False)
      return

    success = self.logic.importGeometry(self.configFile.text, self.inputSelector.currentNode())
    if success == False:
      logging.info('Could not load ultrasound geometry!')
      self.messageLabel.setText('Select input volume!')
      self.fiducialPlacementButton.setChecked(False)
      return

    selectedFiducialNode = self.fiducialSelector.currentNode()
    if selectedFiducialNode == None:
      self.messageLabel.setText('Select output fiducial list!')
      self.fiducialPlacementButton.setChecked(False)
      return

    self.logic.setFiducialNode(selectedFiducialNode)
    self.logic.setMinMaxDepth(self.startingDepthMM.value, self.endingDepthMM.value)
    self.logic.setThreshold(self.thresholdSlider.value)
    self.logic.setMinimumDistanceBetween(self.minimumDistanceBetweenPointsMM.value)
    self.logic.setFiducialArray()

    # Validate the number of scanlines
    if (self.scanlineNumber.value > self.logic.usGeometryLogic.numberOfScanlines):
      slicer.util.errorDisplay(
        "The number of scanlines specified exceeds the maximum of: " + str(logic.usGeometryLogic.numberOfScanlines))
      self.fiducialPlacementButton.setChecked(False)
      return
    if self.scanlineNumber.value < 1:
      logging.warning('At least one scan line should be set')
      self.fiducialPlacementButton.setChecked(False)
      return

    self.logic.computeFiducialScanlines(self.scanlineNumber.value)

    # logic.computeFiducialScanlines(self.scanlineNumber.value)
    self.logic.startTrackingVolumeChanges(self.inputSelector.currentNode())
    # self.fiducialPlacementButton.setStyleSheet('QPushButton {background-color: #cc2900}')
    self.fiducialPlacementButton.setText("Stop fiducial placement")
    self.messageLabel.setText('Scan skull surface...')


  def onConfigureParametersButton(self):
    logic = SkullMarkerLogic(self.configFile.text, self.inputSelector.currentNode(), self.fiducialSelector.currentNode(), self.startingDepthMM.value, self.endingDepthMM.value, self.minimumDistanceBetweenPointsMM.value)

    if (SkullMarkerLogic.configuring == 0): # Configuring off, so begin configuration
      SkullMarkerLogic.configuring = 1
      self.logic.computeFiducialScanlines(self.scanlineNumber.value)
      self.logic.startTrackingVolumeChanges(self.inputSelector.currentNode())
      self.configureParametersButton.setStyleSheet('QPushButton {background-color: #cc2900}')
      self.configureParametersButton.setText("Stop configuring threshold")

    else: # Configuring was on, so stop
      SkullMarkerLogic.configuring = 0
      self.logic.stopTrackingVolumeChanges(self.inputSelector.currentNode())
      self.configureParametersButton.setStyleSheet('QPushButton {background-color: #e67300}')
      self.configureParametersButton.setText("Begin configuring threshold")
      self.fiducialSelector.currentNode().RemoveAllMarkups()


  def validateStartingDepth(self):
    if (self.startingDepthMM.value > self.endingDepthMM.value):
      slicer.util.warningDisplay("Starting depth must be smaller than or equal to ending depth, setting starting depth to equal ending depth.")
      self.startingDepthMM.setValue(self.endingDepthMM.value)


  def validateEndingDepth(self):
    if (self.endingDepthMM.value < self.startingDepthMM.value):
      slicer.util.warningDisplay("Ending depth must be greater than or equal to ending depth, setting ending depth to equal starting depth.")
      self.endingDepthMM.setValue(self.startingDepthMM.value)


  def setThreshold(self):
    SkullMarkerLogic.threshold = self.thresholdSlider.value

  def validateMinimumDistance(self):
    if (self.minimumDistanceBetweenPointsMM.value < 0):
      slicer.util.warningDisplay("The minimum distance between points must be larger than 0mm.")
      self.minimumDistanceBetweenPointsMM.setValue(2)

  def updateGui(self):
    readyToRun = True

    if os.path.isfile(self.configFile.text) == None:
      readyToRun = False

    if self.fiducialSelector.currentNode == None:
      readyToRun = False

    if self.inputSelector.currentNode() == None:
      readyToRun = False

    if readyToRun == True:
      self.fiducialPlacementButton.enabled = True
      self.configureParametersButton.enabled = True
    # else:
      # self.fiducialPlacementButton.enabled = False
      # self.configureParametersButton.enabled = False


#
# SkullMarkerLogic
#
class SkullMarkerLogic(ScriptedLoadableModuleLogic):

  def __init__(self, parent = None):
    ScriptedLoadableModuleLogic.__init__(self, parent)
    self.fiducialScanlines = []
    self.threshold = 0
    self.fiducialNodeId = None
    self.usGeometryLogic = None
    self.minDepthMm = 0
    self.maxDepthMm = 0
    self.threshold = 200
    self.minDistanceBetween = 0
    self.fiducialArray = None

    self.volumeModifiedObserverTag = None


  def importGeometry(self, configFile, inputVolume):
    if inputVolume == None:
      logging.warning('inputVolume == None')
      return False

    if configFile == None:
      logging.warning('configFile == None')
      return False

    import USGeometry
    self.usGeometryLogic = USGeometry.USGeometryLogic()

    setupSuccess = self.usGeometryLogic.setup(configFile, inputVolume)
    if setupSuccess == False:
      logging.error('Could not set up ultrasound geometry from config file: ' + str(configFile))
      return False

    return True


  def setFiducialNode(self, fiducialNode):
    if fiducialNode == None:
      self.fiducialNodeId = None
      return
    self.fiducialNodeId = fiducialNode.GetID()

  def setMinMaxDepth(self, minDepthMm, maxDepthMm):
    self.minDepthMm = minDepthMm
    self.maxDepthMm = maxDepthMm

  def setMinimumDistanceBetween(self,minDistanceBewteen):
    self.minDistanceBetween = minDistanceBewteen

  def setThreshold(self, t):
    self.threshold = t

  def setFiducialArray(self):
    self.fiducialArray = None

  def computeFiducialScanlines(self, scanlineNumber):
    # Find the middle scanline which will always be used
    midScanlineNumber = (self.usGeometryLogic.numberOfScanlines - 1) / 2
    midScanline = self.usGeometryLogic.scanlineEndPoints(midScanlineNumber)
    self.fiducialScanlines.append(midScanline)

    # Compute the interval between scanlines for even spacing
    scanlinesPerHalf = scanlineNumber / 2  # How many scanlines there will be per half
    scanlineInterval = 1
    if (scanlinesPerHalf > 0):  # If only 1 scanline there will not be any interval since only middle scanline is used
      scanlineInterval = midScanlineNumber / scanlinesPerHalf  # Number of scanlines to move between each scanline used for fiducials

    # If there is an even number of scanlines an extra scanline will need to be added after loop to make up for offset
    evenNumberOfScanlines = False
    if (scanlineNumber % 2 == 0):
      scanlinesPerHalf -= 1  # Decrease by one otherwise loop would result in an extra scanline
      evenNumberOfScanlines = True
    for i in range(scanlinesPerHalf):
      # Compute and add scanline to right of middle
      rightScanline = self.usGeometryLogic.scanlineEndPoints(midScanlineNumber + ((i + 1) * scanlineInterval))
      self.fiducialScanlines.append(rightScanline)
      # Compute and add scanline to left of middle
      leftScanline = self.usGeometryLogic.scanlineEndPoints(midScanlineNumber - ((i + 1) * scanlineInterval))
      self.fiducialScanlines.append(leftScanline)

    # If there was an even number of scanlines, add the extra scanline
    if (evenNumberOfScanlines):
      additionalScanline = self.usGeometryLogic.scanlineEndPoints(
        midScanlineNumber + ((scanlinesPerHalf + 1) * scanlineInterval))  # Added to right arbitrarily
      self.fiducialScanlines.append(additionalScanline)


  def startTrackingVolumeChanges(self, inputVolume):
    if inputVolume == None:
      logging.warning('None give instead of inputVolume')
      return

    self.volumeModifiedObserverTag = inputVolume.AddObserver('ModifiedEvent', self.onVolumeModified)


  def stopTrackingVolumeChanges(self, inputVolume):
    if self.volumeModifiedObserverTag != None:
      inputVolume.RemoveObserver(self.volumeModifiedObserverTag)
    self.volumeModifiedObserverTag = None


  def onVolumeModified(self, volumeNode, event):
    # Fiducials for bone surface will be placed between these two values
    self.startingDepthPixel = int(self.minDepthMm / self.usGeometryLogic.outputImageSpacing[1])
    self.endingDepthPixel = int(self.maxDepthMm / self.usGeometryLogic.outputImageSpacing[1])

    if volumeNode == None:
      logging.error('volumeNode == None')
      return

    if volumeNode.IsA('vtkMRMLScalarVolumeNode') == False:
      logging.error('volumeNode is not a vtkMRMLScalarVolumeNode')
      return

    currentImageData = slicer.util.array(volumeNode.GetID())
    ijkToRas = vtk.vtkMatrix4x4()
    volumeNode.GetIJKToRASMatrix(ijkToRas)
    parentTransform = volumeNode.GetParentTransformNode()
    if parentTransform != None:
      parentToRasMatrix = vtk.vtkMatrix4x4()
      parentTransform.GetMatrixTransformToWorld(parentToRasMatrix)
      vtk.vtkMatrix4x4.Multiply4x4(parentToRasMatrix, ijkToRas, ijkToRas)
    fiducialNode = slicer.util.getNode(self.fiducialNodeId)
    if fiducialNode == None:
      logging.error('Fiducial node not found!')
      return

    if self.fiducialArray == None:
      self.fiducialArray = np.reshape([],(0,3))

    modifyFlag = fiducialNode.StartModify()
    # If configuring, only keep max two frames of scanline fiducials
    # if (SkullMarkerLogic.configuring == 1 and self.fiducialNode.GetNumberOfFiducials() >= len(
    #         self.fiducialScanlines) * 2):
    #   self.fiducialNode.RemoveAllMarkups()
    for i in range(len(self.fiducialScanlines)):
      [scanlineStartPoint, scanlineEndPoint] = self.fiducialScanlines[i]
      # Because we are dealing with linear we can just iterate down a column and do not need to use vtkLineSource as for curvilinear - can be added
      startPoint = (scanlineStartPoint[0], self.startingDepthPixel, 0, 1)
      endPoint = (scanlineEndPoint[0], self.endingDepthPixel, 0, 1)

      # Determine if there is a bone surface point on scanline
      currentScanline = currentImageData[0, :, startPoint[0]]
      boneSurfacePoint = self.scanlineBoneSurfacePoint(currentScanline, startPoint, endPoint, self.threshold)

      # Add bone surface point fiducial
      if boneSurfacePoint is not None:
        rasBoneSurfacePoint = ijkToRas.MultiplyPoint(boneSurfacePoint)
        rasBoneSurfacePoint = self.checkDistances(rasBoneSurfacePoint, self.fiducialArray)
        if rasBoneSurfacePoint is not None:
          self.fiducialArray = np.append(self.fiducialArray, [rasBoneSurfacePoint[:3]], axis=0)
          fiducialNode.AddFiducialFromArray(rasBoneSurfacePoint[:3])

      fiducialNode.EndModify(modifyFlag)

  def checkDistances(self, rasBoneSurfacePoint, fiducialArray):
    tooCloseCheck = False
    totalPointsSoFar = len(fiducialArray)
    numChecked=0
    while ((numChecked < totalPointsSoFar) and (tooCloseCheck==False)):
      currentPoint = fiducialArray[numChecked]
      distanceBetweenPoints = np.linalg.norm(currentPoint - rasBoneSurfacePoint[:3])

      '''
      distanceX = (rasBoneSurfacePoint[0] - currentPoint[0])*(rasBoneSurfacePoint[0]-currentPoint[0])
      distanceY = (rasBoneSurfacePoint[1] - currentPoint[1])*(rasBoneSurfacePoint[1]-currentPoint[1])
      distanceZ = (rasBoneSurfacePoint[2] - currentPoint[2])*(rasBoneSurfacePoint[2]-currentPoint[2])
      distanceBetweenPoints = math.sqrt(distanceX+distanceY+distanceZ)
      '''
      if (distanceBetweenPoints<self.minDistanceBetween):
        tooCloseCheck = True

      else:
        numChecked = numChecked + 1

    if (tooCloseCheck == True):
      return None
    else:
      return rasBoneSurfacePoint

  def scanlineBoneSurfacePoint(self, currentScanline, startPoint, endPoint, threshold):
    boneSurfacePoint = None
    boneSurfacePointValue = None
    boneAreaDepth = self.endingDepthPixel - self.startingDepthPixel
    for offset in range(boneAreaDepth):
      currentPixelValue = currentScanline[int(startPoint[1]) + offset]
      # Only consider pixels above specified threshold
      if (currentPixelValue > threshold):
        # Check for artifact
        # ***Note: currently testing w/ magic numbers***
        pointIsNotArtifact = True
        pixelAboveOffset = int( offset - 3 )
        pixelBelowOffset = int( offset + 3 )
        pixelAboveAverage = int(currentScanline[int(startPoint[1]) + pixelAboveOffset])
        pixelBelowAverage = int(currentScanline[int(startPoint[1]) + pixelBelowOffset])
        averageRange = 3
        for i in range(averageRange):
          pixelAboveAverage += currentScanline[int(startPoint[1]) + pixelAboveOffset - i]
          pixelBelowAverage += currentScanline[int(startPoint[1]) + pixelBelowAverage + i]
        pixelAboveAverage /= averageRange
        pixelBelowAverage /= averageRange

        cutoff = currentPixelValue * 0.40
        if (pixelAboveAverage < cutoff and pixelBelowAverage < cutoff):
          pointIsNotArtifact = False

        # Check for intensity increase/decrease (ie ridge)
        pointIsRidge = False
        gradientCheckLength = 5
        aboveDifferenceSum = belowDifferenceSum = 0
        previousAbovePixelValue = previousBelowPixelValue = int(currentPixelValue)
        for i in range(1, gradientCheckLength + 1):  # +1 because we don't consider potential pixel point
          abovePixelValue = int(currentScanline[int(startPoint[1]) + offset - i])
          belowPixelValue = int(currentScanline[int(startPoint[1]) + offset + i])
          aboveDifferenceSum += (previousAbovePixelValue - abovePixelValue)
          currentBelowDifference = belowPixelValue - previousBelowPixelValue
          belowDifferenceSum += (belowPixelValue - previousBelowPixelValue)
          previousAbovePixelValue = abovePixelValue
          previousBelowPixelValue = belowPixelValue

        if (aboveDifferenceSum > 0 and belowDifferenceSum < 0):
          pointIsRidge = True

        if (pointIsNotArtifact and pointIsRidge):
          boneSurfacePoint = (int(startPoint[0]), int(startPoint[1]) + offset, 0, 1)

    return boneSurfacePoint


class SkullMarkerTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """


  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)


  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SkullMarker1()


  def test_SkullMarker1(self):

    self.delayDisplay('Test passed!')
