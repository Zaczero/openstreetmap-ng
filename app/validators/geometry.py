from pydantic import PlainValidator

from app.lib.geo_utils import validate_geometry

GeometryValidator = PlainValidator(validate_geometry)