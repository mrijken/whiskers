from pyramid.renderers import get_renderer
from whiskers import models


def version_view(request):
    main = get_renderer('whiskers:views/templates/master.pt').implementation()
    session = models.DBSession()
    version_id = request.matchdict['version_id']
    version = session.query(models.Version).filter_by(id=int(version_id)).one()
    return {'version': version, 'main': main}


def get_version(version):
    """Returns version id for package"""

    session = models.DBSession()
    existing_version = session.query(models.Version).filter_by(version=version)

    if existing_version.count():
        return existing_version.first().id
    else:
        new_version_id = add_version(version)
        return new_version_id


def add_version(package, version):
    """Adds new version and returns its id"""

    session = models.DBSession()
    existing_version = session.query(models.Version).filter_by(version=version)

    if not existing_version.count():
        new_version = models.Version(version)
        session.merge()
        return new_version.id
