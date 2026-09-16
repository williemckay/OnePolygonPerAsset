@ echo off
echo: >> C:\Scripts\OnePolygonPerAsset\OnePolygonPerAsset.log
echo: >> C:\Scripts\OnePolygonPerAsset\OnePolygonPerAsset.log
echo Process Started on %date% at %time% >> C:\Scripts\OnePolygonPerAsset\OnePolygonPerAsset.log

echo Starting Asset MonoPolygonising Processing at %date% %time% >> C:\Scripts\OnePolygonPerAsset\OnePolygonPerAsset.log
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" "C:\Scripts\OnePolygonPerAsset\CreateOnePolygonPerAssets.py" >> C:\Scripts\OnePolygonPerAsset\OnePolygonPerAsset.log
echo Scripts complete at %date% %time% >> C:\Scripts\OnePolygonPerAsset\OnePolygonPerAsset.log