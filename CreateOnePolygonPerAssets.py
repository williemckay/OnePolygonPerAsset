import arcpy
import os
import shutil
import tempfile
import zipfile
from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection, FeatureLayer

gis = GIS('home')

flayer = gis.content.get('785a9a9dd604477aba4425ff5d12be13')
layer = flayer.layers[0]

SDE_CONNECTION = (    
    r"\\gisdata\gis\Department\Environmental_Management"
    r"\CatchmentOperations\Assets\AGOL_Publishing"
    r"\OnePolygonPerAsset\GISLiveDB_water.sde"
)

OUTPUT_GDB = (
    r"\\gisdata\GIS\Department\Environmental_Management"
    r"\CatchmentOperations\Assets\AGOL_Publishing"
    r"\OnePolygonPerAsset\OnePolygonPerAsset.gdb"
)

# Replace these with the actual source feature class paths
POINTS_SOURCE = os.path.join(
        SDE_CONNECTION,
        "WATER.GISADMIN.RiverManagement_AssetPoint"
)

LINES_SOURCE = os.path.join(
    SDE_CONNECTION,
    "WATER.GISADMIN.RiverManagement_AssetPolyline"
)

POLYGONS_SOURCE = os.path.join(
    SDE_CONNECTION,
    "WATER.GISADMIN.RiverManagement_AssetPolygon"
)

def main():

    arcpy.env.overwriteOutput = True

    print("Creating In Service asset polygons...")

    # Outputs
    rm_points = os.path.join(OUTPUT_GDB, "RM_Points")
    rm_points_buffer = os.path.join(OUTPUT_GDB, "RM_Points_Buffer")

    rm_lines = os.path.join(OUTPUT_GDB, "RM_Lines")
    rm_lines_buffer = os.path.join(OUTPUT_GDB, "RM_Lines_Buffer")

    rm_polygons = os.path.join(OUTPUT_GDB, "RM_Polygons")
    rm_polygons_buffer = os.path.join(OUTPUT_GDB, "RM_Polygons_Buffer")

    all_assets = os.path.join(OUTPUT_GDB, "RM_AllAssets_Buffered")
    in_service_assets = os.path.join(OUTPUT_GDB, "RM_One_Polygon_Per_Inservice_Asset")

    # Common selection
    where_clause = """
        AMIS_GisKey IS NOT NULL
        AND AMIS_ServiceStatus IN (
            'In Service',
            'In Service - Upgrade',
            'Pending'
        )
        AND GIS_Asset_Status NOT IN (
            'Error',
            'Test',
            'Historic'
        )
    """

    # -----------------------------------------------------------------------
    # Points
    # -----------------------------------------------------------------------

    print("Processing points...")

    arcpy.analysis.Select(
        POINTS_SOURCE,
        rm_points,
        where_clause
    )

    arcpy.analysis.Buffer(
        rm_points,
        rm_points_buffer,
        "3 Meters"
    )

    # -----------------------------------------------------------------------
    # Lines
    # -----------------------------------------------------------------------

    print("Processing lines...")

    arcpy.analysis.Select(
        LINES_SOURCE,
        rm_lines,
        where_clause
    )

    arcpy.analysis.Buffer(
        rm_lines,
        rm_lines_buffer,
        "3 Meters"
    )

    # -----------------------------------------------------------------------
    # Polygons
    # -----------------------------------------------------------------------

    print("Processing polygons...")

    polygon_where = (
        where_clause +
        " AND AMIS_AssetClass2 NOT IN ('Scheme')"
    )

    arcpy.analysis.Select(
        POLYGONS_SOURCE,
        rm_polygons,
        polygon_where
    )

    arcpy.analysis.Buffer(
        rm_polygons,
        rm_polygons_buffer,
        "1 Meters"
    )

    # -----------------------------------------------------------------------
    # Merge
    # -----------------------------------------------------------------------

    print("Merging assets...")

    arcpy.management.Merge(
        [
            rm_points_buffer,
            rm_lines_buffer,
            rm_polygons_buffer
        ],
        all_assets
    )

    # -----------------------------------------------------------------------
    # Dissolve
    # -----------------------------------------------------------------------

    print("Dissolving by asset...")

    dissolve_fields = [
        "AMIS_GisKey",
        "AMIS_AssetName",
        "AMIS_AssetID",
        "AMIS_AssetClass1",
        "AMIS_AssetClass2",
        "AMIS_Scheme",
        "AMIS_LegacyID",
        "AMIS_ServiceStatus"
    ]

    arcpy.management.Dissolve(
        all_assets,
        in_service_assets,
        dissolve_fields
    )

    return in_service_assets

    print("Local processing complete.")



def append_to_agol(in_service_assets, gis, layer):

    # ---------------------------------------------------------
    # Create temporary File GDB
    # ---------------------------------------------------------

    temp_dir = tempfile.mkdtemp()
    temp_gdb = os.path.join(temp_dir, "upload.gdb")

    arcpy.management.CreateFileGDB(
        temp_dir,
        "upload.gdb"
    )

    temp_fc = os.path.join(
        temp_gdb,
        "RM_One_Polygon_PerInService_Asset"
    )

    arcpy.management.CopyFeatures(
        in_service_assets,
        temp_fc
    )

    print("Temporary File GDB created.")

    # ---------------------------------------------------------
    # Zip the File GDB
    # ---------------------------------------------------------

    zip_path = os.path.join(
        temp_dir,
        "RM_One_Polygon_PerInService_Asset.zip"
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
     ) as zipf:

        for root, dirs, files in os.walk(temp_gdb):

            for file in files:

                # ArcGIS lock files should not be included
                if file.endswith(".lock"):
                    continue

                file_path = os.path.join(root, file)

                arcname = os.path.relpath(
                    file_path,
                    temp_dir
                )

                zipf.write(
                    file_path,
                    arcname
                )

    print(f"Created {zip_path}")

    # ---------------------------------------------------------
    # Upload temporary FGDB to AGOL
    # ---------------------------------------------------------

    temp_item = gis.content.add(
        {
            "title": "RM_One_Polygon_PerInService_Asset_temp",
            "type": "File Geodatabase"
        },
        data=zip_path
    )

    print("Temporary File GDB uploaded.")

    try:

        # -----------------------------------------------------
        # Delete existing features
        # -----------------------------------------------------

        print("Deleting existing hosted features...")

        layer.delete_features(
            where="1=1"
        )

        # -----------------------------------------------------
        # Append new features
        # -----------------------------------------------------

        print("Appending new features...")

        print("Append supported:", layer.properties.supportsAppend)

        print("Hosted fields:")
        for field in layer.properties.fields:
            print(field["name"], field["type"])

        print("Source fields:")

        for field in arcpy.ListFields(temp_fc):
            print(field.name, field.type)

        result = layer.append(
            item_id=temp_item.id,
            upload_format="filegdb",
            source_table_name="RM_One_Polygon_PerInService_Asset",
            upsert=False
        )

        print(result)

        if not result:
            raise RuntimeError("AGOL append failed.")

        print("Append successful.")

    finally:

        # -----------------------------------------------------
        # Remove temporary AGOL item and local files
        # -----------------------------------------------------

        temp_item.delete()
        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        print("Temporary files removed.")


if __name__ == "__main__":
    in_service_assets = main()

    append_to_agol(
    in_service_assets,
    gis,
    layer
    )
