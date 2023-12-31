from fastapi import APIRouter

from src.lib_cython.xmltodict import XAttr

router = APIRouter()


@router.get('/versions')
@router.get('/versions.xml')
@router.get('/versions.json')
async def legacy_versions() -> dict:
    return {'api': {XAttr('versions', custom_xml='version'): ['0.6']}}
