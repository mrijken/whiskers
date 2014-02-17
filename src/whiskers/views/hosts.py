from pyramid.renderers import get_renderer
from sqlalchemy.orm.exc import NoResultFound
from whiskers import models


class HostsView(object):

    def __init__(self, request):
        self.main = get_renderer(
            'whiskers:views/templates/master.pt').implementation()
        self.request = request

    def __call__(self):
        """Hosts main view."""
        query = self.hosts_info
        return {'results': query, 'main': self.main}

    def host_view(self):
        host_id = self.request.matchdict['host_id']
        try:
            host = models.Host.get_by_id(int(host_id))
            buildouts = self.get_buildouts(host_id)
        except NoResultFound as e:
            host = None
            buildouts = []
        return {'host': host,
                'main': self.main,
                'buildouts': buildouts}

    @property
    def hosts_info(self):
        """Return list of dicts containing Host info."""

        result_list = []

        results = models.DBSession.query(models.Host).\
            join(models.Buildout, models.Buildout.host_id == models.Host.id).all()

        for result in results:
            tmp = {'host': result, 'count': self.get_unique_buildouts(result)}
            result_list.append(tmp)

        return result_list

    def get_unique_buildouts(self, host):
        """Return amount of buildouts (grouped by name)."""

        results = models.DBSession.query(models.Buildout).\
            filter(models.Buildout.host == host).\
            group_by(models.Buildout.name)

        return results.count()

    def get_buildouts(self, host_id):
        """Return list of buildouts."""
        results = models.DBSession.query(models.Buildout).\
            filter(models.Buildout.host_id == host_id).\
            group_by(models.Buildout.name).\
            order_by(models.Buildout.datetime.desc()).all()
        return results
