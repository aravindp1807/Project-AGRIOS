def get_gibs_tile_url(layer: str, date_str: str) -> str:
    """
    Returns the templated NASA GIBS Web Mercator (EPSG:3857) tile URL for MapLibre.
    """
    # Pattern: https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/{tileMatrixSet}/{z}/{y}/{x}.png
    # tileMatrixSet is GoogleMapsCompatible_Level9 for standard Z/Y/X Web Mercator tile grid.
    return (
        f"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/"
        f"{date_str}/GoogleMapsCompatible_Level9/{{z}}/{{y}}/{{x}}.png"
    )
