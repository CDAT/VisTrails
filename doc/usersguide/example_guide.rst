.. _chap-example_guide:

********************************
Module Descriptions and Examples
********************************

.. index:: VisTrails VTK modules

VisTrails VTK modules
=====================

Although most VTK modules in VisTrails would be familiar to vtk users, or at least in the vtk documentation, there are a few modules that VisTrails introduces.  They are used as follows:

* **PythonSource** - Although a PythonSource is in the Basic Modules list rather than VTK, it is mentioned here for convenience.  This module allows you write python statements to be executed as part of the workflow.  See Section :ref:`sec-pythonsource` for more information.

* **VTKCell** - VTKCell is a VisTrails module that can display a vtkRenderWindow inside a cell.  Simply pass it a vtkRenderer and any additional optional inputs, and it will display the results in the spreadsheet.

* **VTKRenderOffscreen** - Takes the output of a vtkRenderer and produces a PNG image of size width X height.  Default values of width and height are 512.  The output can then be written to a file using a FileSink.

* **VTKViewCell** - This is similar to the VTKCell except that you pass it a vtkRenderView.

* **vtkInspectors: vtkDataArrayInspector, vtkDataSetAttributesInspector, vtkDataSetInspector, vtkPolyDataInspector** - These inspectors were created to allow easy access to information that is not otherwise exposed by module ports, but would be accessible through vtk objects.  This information includes: normals, scalars, tensors, and vectors as well as statistical information such as bounds, center, length, max, min.  Looking at the output ports of these inspectors gives an idea of the information available.

.. index:: vtkInteractionHandler

* **vtkInteractionHandler** - The vtkInteractionHandler is used when a callback function is needed.  To setup this handler:

   * Connect the Observer input port to the output port of the object that needs the callback function.  
   * Connect the SharedData input port to the modules that would be passed as parameters to the callback function.  Multiple modules can be connected (see terminator.vt - Images Slices SW).
   * Connect the output port to the VTKCell.
   * Select configure to write the callback function.

      * Name the function after the event that initiates it, but replace 'Event' with 'Handler'.  If the function should be called when a ``StartInteractionEvent`` occurs, the function should be named ``startInteractionHandler``.
      * The function should take the parameters observer, and shareddata.
      * Add the contents of the function.

   There are a number of examples that use the vtkInteractionHandler.  If there is any confusion, comparing the callback/interaction handler portions of the .py and .vt files in the vtk_examples/GUI directory is helpful.

   **Accessing vtkObjects in vtkInteractionHandler** VtkObjects passed to the vtkInteractionHandler are VisTrails modules.  The vtkObject within that module is called a vtkInstance and is accessed by calling myModule.vtkInstance.  See Section :ref:`sec-pythonsource` for more information.

* **vtkScaledTransferFunction** - Allows you to add a transfer function through the use of an interactive widget.  See head.vt - volume rendering or terminator.vt for example usage.

.. _sec-module-example:

Modules and Corresponding Examples
==================================

Here we provide a list of the .vt files in the examples directory that use the following modules:

.. index:: 
   pair: modules; list of examples

* **AreaFilter**: 
   triangle_area.vt
   offscreen.vt, terminator.vt, vtk.vt
   KEGG_SearchEntities_webservice.vt
   triangle_area.vt
   structure_or_id_webservice.vt, protein_visualization.vt
   offscreen.vt - offscreen
   triangle_area.vt
   structure_or_id_webservice.vt, protein_visualization.vt
   r_stats.vt
   triangle_area.vt
   triangle_area.vt
   plot.vt, terminator.vt - Histrogram, triangle_area.vt, vtk.vt - Three Cells
   plot.vt, terminator.vt - Histrogram, triangle_area.vt, vtk.vt - Three Cells
   plot.vt, terminator.vt - Histrogram, triangle_area.vt, vtk.vt - Three Cells
   ProbeWithPointWidget.vt, officeTube.vt
   infovis.vt, noaa_webservices.vt, offscreen.vt, KEGG_SearchEntities_webservice.vt, chebi_webservice.vt, EMBOSS_webservices.vt, structure_or_id_webservice.vt, vtk_http.vt, protein_visualization.vt, terminator.vt, triangle_area.vt
   noaa_webservices.vt, offscreen.vt, KEGG_SearchEntities_webservice.vt, chebi_webservice.vt, EMBOSS_webservices.vt, protein_visualization.vt
   r_stats.vt
   r_stats.vt
   r_stats.vt
   offscreen.vt, vtk.vt
   r_stats.vt, triangle_area.vt
   marching.vt, ProbingWithPlaneWidget.vt, TransformWithBoxWidget.vt, BandContourTerrain.vt, probeComb.vt, ImplicitPlaneWidget.vt, BuildUGrid.vt, ProbeWithPointWidget.vt, VolumeRenderWithBoxWidget.vt, PerlinTerrain.vt
   probeComb.vt, BandContourTerrain.vt
   flamingo.vt
   vtk.vt - Implicit Plane Clipper, xyPlot.vt, TransformWithBoxWidget.vt, probeComb.vt, ImplicitPlaneWidget.vt, warpComb.vt
   assembly.vt
   textOrigin.vt
   BandContourTerrain.vt
   Tplane.vt, imageWarp.vt, GenerateTextureCoords.vt
   TransformWithBoxWidget.vt, VolumeRenderWithBoxWidget.vt, cone.vt - 6
   cubeAxes.vt, ClipCow.vt
   ExtractUGrid.vt
   constrainedDelaunay.vt, Arrays.vt, CreateStrip.vt
   terminator.vt, vtk.vt - Implicit Plane Clipper, ImplicitPlaneWidget.vt, ClipCow.vt
   lung.vt, SimpleRayCast.vt, mummy.xml - volume rendering, SimpleTextureMap2D.vt, VolumeRenderWithBoxWidget.vt
   iceCream.vt
   vtk_book_3rd_p193.vt, vtk.vt - Implicit Plane Clipper, TransformWithBoxWidget.vt, Cone.vt, ImplicitPlaneWidget.vt, ProbeWithPointWidget.vt, assembly.vt
   ExtractUGrid.vt, pointToCellData.vt
   brain_vistrail.vt, spx.vt, vtk_http.vt, marching.vt, head.vt - alias, mummy.xml - Isosurface, terminator.vt, pointToCellData.vt, triangle_area.vt - CalculateArea, Medical1.vt, hello.vt, VisQuad.vt, probeComb.vt, vtk_book_3rd_p189.vt, Medical2.vt, iceCream.vt, Contours2D.vt, Medical3.vt, PerlinTerrain.vt, ColorIsosurface.vt, PseudoVolumeRendering.vt
   cubeAxes.vt
   assembly.vt, marching.vt
   ClipCow.vt, CutCombustor.vt, PseudoVolumeRendering.vt
   assembly.vt, cylinder.vt
   CutCombuster.vt, officeTube.vt
   officeTube.vt, CutCombustor.vt
   ProbingWithPlaneWidget.vt, StreamlinesWithLineWidget.vt, CutCombustor.vt, officeTube.vt, TextureThreshold.vt, BandContourTerrain.vt, probeComb.vt, ProbeWithPointWidget.vt, rainbow.vt, streamSurface.vt, warpComb.vt
   offscreen.vt, spx.vt, structure_or_id_webservice.vt, vtk_http.vt, SubsampleGrid.vt, TextureThreshold.vt, imageWarp.vt, protein_visualization.vt, head.vt - alias, mummy.xml - Isosurface, terminator.vt - Histogram, pointToCellData.vt, ExtractUGrid.vt, ExtractGeometry.vt, vtk.vt, BuildUGrid.vt, GenerateTextureCoords.vt
   brain_vistrail.vt, vtk_http.vt, triangle_area.vt, ExtractUGrid.vt, vtk.vt
   smoothFran.vt
   constrainedDelaunay.vt, faultLines.vt
   GenerateTextureCoords.vt
   BandContourTerrain.vt
   Arrays.vt
   constrainedDelaunay.vt, marching.vt
   ExtractGeometry.vt
   SubsampleGrid.vt, PseudoVolumeRendering.vt - vtkPlane
   ExtractUGrid.vt
   Contours2D.vt
   Arrays.vt, BuildUGrid.vt, marching.vt
   textOrigin.vt
   ExtractUGrid.vt, pointToCellData.vt
   vtk_book_3rd_p193.vt, marching.vt, vtk.vt - Implicit Plane Clipper, TransformWithBoxWidget.vt, ImplicitPlaneWidget.vt, ProbeWithPointWidget.vt, spikeF.vt
   infovis.vt
   BuildUGrid.vt
   infovis.vt
   BuildUGrid.vt, marching.vt
   Medical3.vt
   BandContourTerrain.vt, imageWarp.vt
   imageWarp.vt
   brain_vistrail.vt, Medical3.vt
   terminator.vt
   lung.vt - raycasted
   BandContourTerrain.vt
   iceCream.vt, ExtractGeometry.vt
   hello.vt
   terminator.vt, vtk.vt, ImplicitPlaneWidget.vt
   PerlinTerrain.vt
   Arrays.vt
   ProbingWithPlaneWidget.vt, StreamlinesWithLineWidget.vt, terminator.vt, vtk.vt - Implicit Plane Clipper, TransformWithBoxWidget.vt, Cone.vt - 6 , ImplicitPlaneWidget.vt, ProbeWithPointWidget.vt, VolumeRenderWithBoxWidget.vt
   terminator.vt
   Cone.vt - 5
   cubeAxes.vt, faultLines.vt
   BuildUGrid.vt
   streamSurface.vt, xyPlot.vt
   StreamlinesWithLineWidget.vt
   TestText.vt, stl.vt, CADPart.vt, vtk.vt - Implicit Plane Clipper, TransformWithBoxWidget.vt, BandContourTerrain.vt, cubeAxes.vt, ImplicitPlaneWidget.vt, FilterCADPart.vt, ColorIsosurface.vt
   brain_vistrail.vt, vtk_book_3rd_p193.vt, pointToCellData.vt, BandContourTerrain.vt, ExtractUGrid.vt, Medical3.vt, rainbow.vt, PseudoVolumeRendering.vt
   vtk_book_3rd_p193.vt, spikeF.vt
   triangle_area.vt - CalculateArea
   imageWarp.vt
   lung.vt - TextureWithShading
   VisQuad.vt, probeComb.vt, ExtractGeometry.vt, vtk_book_3rd_p189.vt, cubeAxes.vt, VolumeRenderWithBoxWidget.vt, Contours2D.vt, Medical1.vt, Medical2.vt, Medical3.vt
   protein_visualization.vt, structure_or_id_webservice.vt
   PerlinTerrain.vt
   lung.vt, SimpleRayCast.vt, mummy.xml - volume rendering, SimpleTextureMap2D.vt, VolumeRenderWithBoxWidget.vt
   BuildUGrid.vt
   lung.vt - TS and plane, CutCombustor.vt, terminator.vt, vtk.vt - Implicit Plane Clipper, ImplicitPlaneWidget.vt, iceCream.vt, PerlinTerrain.vt, ClipCow.vt
   VolumeRenderWithBoxWidget.vt
   Tplane.vt, terminator.vt, probeComb.vt
   ProbingWithPlaneWidget.vt
   ProbingWithPlaneWidget.vt, StreamlinesWithLineWidget.vt, CutCombustor.vt, SubsampleGrid.vt, TextureThreshold.vt, xyPlot.vt, probeComb.vt, ProbeWithPointWidget.vt, rainbow.vt, ColorIsosurface.vt, streamSurface.vt, warpComb.vt, PseudoVolumeRendering.vt
   marching.vt, Arrays.vt, BuildUGrid.vt
   pointToCellData.vt
   CreateStrip.vt, marching.vt, constrainedDelaunay.vt, Arrays.vt, BuildUGrid.vt
   GenerateTextureCoords.vt, officeTube.vt
   ProbeWithPointWidget.vt
   CreateStrip.vt, ProbingWithPlaneWidget.vt, constrainedDelaunay.vt, StreamlinesWithLineWidget.vt, Arrays.vt, ProbeWithPointWidget.vt, ClipCow.vt
   ClipCow.vt
   brain_vistrail.vt, pointToCellData.vt, Medical1.vt , faultLines.vt, ExtractUGrid.vt, smoothFran.vt, cubeAxes.vt, Medical2.vt, Medical3.vt, ClipCow.vt, ColorIsosurface.vt, warpComb.vt, PerlinTerrain.vt, spikeF.vt, PseudoVolumeRendering.vt, BandContourTerrain.vt
   hello.vt, faultLines.vt, smoothFran.vt, spikeF.vt
   BuildUGrid.vt
   BuildUGrid.vt
   BuildUGrid.vt
   brain_vistrail.vt, ProbingWithPlaneWidget.vt, xyPlot.vt, probeComb.vt, ProbeWithPointWidget.vt
   xyPlot.vt
   BuildUGrid.vt
   BuildUGrid.vt
   spx.vt - Decimate
   VisQuad.vt, ExtractGeometry.vt, vtk_book_3rd_p189.vt, Contours2D.vt
   infovis.vt - hello_world
   offscreen.vt
   StreamlinesWithLineWidget.vt
   streamSurface.vt
   StreamlinesWithLineWidget.vt, officeTube.vt, streamSurface.vt
   VisQuad.vt, ExtractGeometry.vt, vtk_book_3rd_p189.vt, iceCream.vt, Contours2D.vt, PerlinTerrain.vt
   head.vt - volume rendering, terminator.vt
   ExtractGeometry.vt
   marching.vt, filterCADPart.vt
   xyPlot.vt
   iceCream.vt, ExtractGeometry.vt
   TestText.vt, marching.vt, assembly.vt, vtk.vt - Implicit Plane Clipper, TransformWithBoxWidget.vt, ImplicitPlaneWidget.vt
   stl.vt, CADPart.vt, FilterCADPart.vt
   StreamlinesWithLineWidget.vt, officeTube.vt, streamSurface.vt
   brain_vistrail.vt, Medical2.vt, Medical3.vt, ClipCow.vt
   CutCombuster.vt, officeTube.vt, TextureThreshold.vt, rainbow.vt, warpComb.vt
   StreamlinesWithLineWidget.vt, officeTube.vt, SubsampleGrid.vt, TextureThreshold.vt, xyPlot.vt, probeComb.vt, ProbeWithPointWidget.vt, rainbow.vt, ColorIsosurface.vt, streamSurface.vt, warpComb.vt, PseudoVolumeRendering.vt, ProbingWithPlaneWidget.vt, CutCombustor.vt
   officeTube.vt
   lung.vt, vtk_book_3rd_p193.vt, SimpleRayCast.vt, TextureThreshold.vt, head.vt - volume rendering, mummy.xml - volume rendering, head.vt - alias, mummy.xml - Isosurface, terminator.vt, SimpleTextureMap2D.vt
   BuildUGrid.vt
   TestText.vt
   TestText.vt, xyPlot.vt, cubeAxes.vt
   Tplane.vt, TextureThreshold.vt, terminator.vt, GenerateTextureCoords.vt
   GenerateTextureCoords.vt
   pointToCellData.vt
   vtk_book_3rd_p193.vt, marching.vt
   TextureThreshold.vt
   marching.vt, terminator.vt, xyPlot.vt, TransformWithBoxWidget.vt, Cone.vt - 6, probeComb.vt, ExtractGeometry.vt, spikeF.vt
   marching.vt, xyPlot.vt, probeComb.vt, spikeF.vt
   GenerateTextureCoords.vt
   infovis.vt
   infovis.vt
   BuildUGrid.vt
   triangle_area.vt - CalculateArea, ClipCow.vt
   BuildUGrid.vt
   marching.vt, constrainedDelaunay.vt, officeTube.vt, officeTubes.vt, xyPlot.vt, faultLines.vt, PseudoVolumeRendering.vt
   BuildUGrid.vt, marching.vt
   offscreen.vt, spx.vt, pointToCellData.vt
   textOrigin.vt, marching.vt
   BuildUGrid.vt
   infovis.vt
   infovis.vt - cone_layout
   lung.vt, SimpleRayCast.vt, head.vt - volume rendering, mummy.xml - volume rendering, terminator.vt, SimpleTextureMap2D.vt, VolumeRenderWithBoxWidget.vt
   VolumeRenderWithBoxWidget.vt, Medical1.vt, Medical2.vt, Medical3.vt
   lung.vt, SimpleRayCast.vt, head.vt - volume rendering, mummy.xml - volume rendering, terminator.vt, SimpleTextureMap2D.vt, VolumeRenderWithBoxWidget.vt
   lung.vt - raycasted, SimpleRayCast.vt, mummy.xml - volume rendering, terminator.vt - SW, VolumeRenderWithBoxWidget.vt
   lung.vt - raycasted, SimpleRayCast.vt, mummy.xml - volume rendering, terminator.vt - SW, VolumeRenderWithBoxWidget.vt
   SimpleTextureMap2D.vt
   head.vt - volume rendering, terminator.vt - HW
   BuildUGrid.vt
   imageWarp.vt, BandContourTerrain.vt, warpComb.vt
   pointToCellData.vt, ExtractUGrid.vt
   BuildUGrid.vt
   terminator.vt
   infovis.vt
   xyPlot.vt