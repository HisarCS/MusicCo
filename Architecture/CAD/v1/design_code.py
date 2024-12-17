#Author- Emre Dayangaç
#Description-
import adsk.core, adsk.fusion, traceback

def run(context):
    try:
        # App and UI setup
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        rootComp = design.rootComponent

        # Define dimensions
        length = 100  # Length of the box
        width = 60    # Width of the box
        height = 30   # Thickness of the box
        fillet_radius = 5  # Fillet radius
        screen_length = 36  # Length of PiOLED cutout
        screen_width = 13   # Width of PiOLED cutout
        offset_from_top = 10  # Distance of OLED cutout from top edge

       
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        sketch = sketches.add(xyPlane)


        lines = sketch.sketchCurves.sketchLines
        point0 = adsk.core.Point3D.create(0, 0, 0)
        point1 = adsk.core.Point3D.create(length, 0, 0)
        point2 = adsk.core.Point3D.create(length, width, 0)
        point3 = adsk.core.Point3D.create(0, width, 0)

        lines.addByTwoPoints(point0, point1)
        lines.addByTwoPoints(point1, point2)
        lines.addByTwoPoints(point2, point3)
        lines.addByTwoPoints(point3, point0)


        prof = sketch.profiles[0]
        extrudes = rootComp.features.extrudeFeatures
        extrudeInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(height)
        extrudeInput.setDistanceExtent(False, distance)
        extrude = extrudes.add(extrudeInput)
        body = extrude.bodies[0]


        fillets = rootComp.features.filletFeatures
        edgeCollection = adsk.core.ObjectCollection.create()
        for edge in body.edges:
            edgeCollection.add(edge)

        filletInput = fillets.createInput()
        filletInput.addConstantRadiusEdgeSet(edgeCollection, adsk.core.ValueInput.createByReal(fillet_radius), True)
        fillets.add(filletInput)


        topPlaneInput = rootComp.constructionPlanes.createInput()
        offsetValue = adsk.core.ValueInput.createByReal(height)
        topPlaneInput.setByOffset(rootComp.xYConstructionPlane, offsetValue)
        topPlane = rootComp.constructionPlanes.add(topPlaneInput)


        sketchScreen = sketches.add(topPlane)

        screenX = (length - screen_length) / 2
        screenY = width - screen_width - offset_from_top  
        point0 = adsk.core.Point3D.create(screenX, screenY, 0)
        point1 = adsk.core.Point3D.create(screenX + screen_length, screenY, 0)
        point2 = adsk.core.Point3D.create(screenX + screen_length, screenY + screen_width, 0)
        point3 = adsk.core.Point3D.create(screenX, screenY + screen_width, 0)

        linesScreen = sketchScreen.sketchCurves.sketchLines
        linesScreen.addByTwoPoints(point0, point1)
        linesScreen.addByTwoPoints(point1, point2)
        linesScreen.addByTwoPoints(point2, point3)
        linesScreen.addByTwoPoints(point3, point0)

   
        cutoutProf = sketchScreen.profiles[0]
        cutoutInput = extrudes.createInput(cutoutProf, adsk.fusion.FeatureOperations.CutFeatureOperation)
        cutoutDepth = adsk.core.ValueInput.createByReal(-10)  # Negative to cut downward
        cutoutInput.setDistanceExtent(False, cutoutDepth)
        extrudes.add(cutoutInput)


        ui.messageBox('Rectangular box with OLED screen cutout moved higher created successfully!')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
