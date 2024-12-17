import adsk.core, adsk.fusion, traceback

def run(context):
    try:
     
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = app.activeProduct
        rootComp = design.rootComponent

    
        length = 100 
        width = 60    
        height = 30   
        fillet_radius = 5  
        screen_length = 36  
        screen_width = 13   
        offset_from_top = 10  
        button_size = 10  
        circle_diameter = 8 
        button_height = 4  
        square_button_size = 10
        square_button_spacing = 5  
        square_offset_x = 90


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
        cutoutDepth = adsk.core.ValueInput.createByReal(-5)
        cutoutInput.setDistanceExtent(False, cutoutDepth)
        extrudes.add(cutoutInput)


        sketchButtons = sketches.add(topPlane)
        spacing = (length - 7 * circle_diameter) / 8  

        
        for i in range(7):
            centerX = spacing + (i+0.25) * (circle_diameter + spacing)
            centerY = width / 3 
            sketchButtons.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(centerX, centerY, 0), circle_diameter / 2
            )
        

        for side in [-0.1, 0.5]:  
            for i in range(2): 
                buttonX = screenX + (square_offset_x * side) 
                buttonY = (screenY-5) + i * (square_button_size + square_button_spacing)

                sketchButtons.sketchCurves.sketchLines.addCenterPointRectangle(
                    adsk.core.Point3D.create(buttonX, buttonY, 0),
                    adsk.core.Point3D.create(buttonX + square_button_size / 2, buttonY + square_button_size / 2, 0)
                )


        for profile in sketchButtons.profiles:
            extrudeInput = extrudes.createInput(profile, adsk.fusion.FeatureOperations.JoinFeatureOperation)
            extrudeInput.setDistanceExtent(False, adsk.core.ValueInput.createByReal(button_height))
            extrudes.add(extrudeInput)


        for profile in sketchButtons.profiles:
            extrudeInput = extrudes.createInput(profile, adsk.fusion.FeatureOperations.JoinFeatureOperation)
            extrudeHeight = adsk.core.ValueInput.createByReal(button_height)
            extrudeInput.setDistanceExtent(False, extrudeHeight)
            extrudes.add(extrudeInput)

        

        ui.messageBox('Box with OLED screen and protruding circular buttons created successfully!')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
