import zlib
import logging
import json

from datetime import datetime

from pyramid.response import Response
from pyramid.renderers import get_renderer
from pyramid.httpexceptions import HTTPFound

from whiskers.jsonwrapper import JsonDataWrapper
from whiskers import models


class BuildoutsView(object):
    """Buildout views."""

    def __init__(self, request):
        self.main = get_renderer(
            'whiskers:views/templates/master.pt').implementation()
        self.request = request

    def __call__(self):
        """Main view for whiskers/buildouts."""

        buildouts = self.get_buildouts_info()

        return {'buildouts': buildouts,
                'project': 'whiskers',
                'main': self.main}

    def get_buildouts_info(self):
        """Return list of dicts containing Buildout info."""

        query = models.DBSession.query(models.Buildout).\
            join(models.Buildout.host).\
            group_by(models.Buildout.name).\
            order_by(models.Buildout.datetime).\
            all()

        return query

    def post(self):
        """Add a new buildout to database."""
        import urllib
        try:
#            data = json.loads(urllib2.unquote(self.request.body).replace('+','')[len("data="):])
            data = json.loads(urllib.unquote_plus(self.request.body)[len("data="):])
            checksum = zlib.adler32(self.request.body)
            checksum_buildout = models.Buildout.get_by_checksum(checksum)
            if checksum_buildout:
                logging.info("Checksum matched")
                logging.info("Updating datetime..")
                checksum_buildout.datetime = datetime.now()
                models.DBSession.flush()
                raise Exception("No changes with existing data.")
            logging.info("New checksum")
            jsondata = JsonDataWrapper(data)
        except KeyError:
            return Response(u"No data. Nothing added.")
        except AttributeError as e:
            return Response(u"Not a valid request. Error was: {error}".format(
                error=str(e)))
        except Exception as e:
            return Response(u"Adding information failed. Error was: {error}".
                            format(error=str(e)))

        host = models.Host.get_by_name(jsondata.hostname)

        if not host:
            host = models.Host.add(jsondata.hostname, jsondata.ipv4)

        self.add_buildout(jsondata, host, checksum)

        return Response(u'Added buildout information to Whiskers.')

    def add_buildout(self, data, host, checksum):
        packages = []

        for package_info in data.packages:
            package = models.Package.get_by_nameversion(package_info['name'],
                                                 package_info['version'])
            if not package:
                equation = package_info.get('equation', None)
                version = models.Version.get_by_version(package_info['version']) or\
                    models.Version.add(package_info['version'], equation)
                requirements = self.get_requirements(
                    package_info['requirements'], data.versionmap)
                package = models.Package.add(package_info['name'],
                                      version,
                                      requirements)

            packages.append(package)

        buildout = models.Buildout(data.name, host, checksum, started=data.started,
                            finished=data.finished, packages=packages,
                            config=data.config)

        models.DBSession.add(buildout)
        self.remove_old_buildouts(data.name, host)
        return buildout

    def remove_old_buildouts(self, name, host):
        """Remove old buildouts."""
        buildouts_to_keep = models.Settings.get_buildouts_to_keep()
        buildouts = models.Buildout.get_by_name_host(name, host)

        if buildouts.count() > buildouts_to_keep and buildouts_to_keep > 0:
            for buildout in buildouts[buildouts_to_keep:]:
                models.DBSession.delete(buildout)

    def get_requirements(self, requirements, versionmap):
        """Return list of package requirements."""
        packages = []

        for req in requirements:
            name = req.get('name')
            version = req.get('version')
            # Below version related code is crap
            # TODO: Clean the crap
            if not version:
                try:
                    version = versionmap[name]
                except KeyError:
                    version = 'stdlib'
            else:
                if version != versionmap[name]:
                    version = versionmap[name]
            package = models.Package.get_by_nameversion(name,
                                                 version)
            if not package:
                equation = req.get('equation', None)
                version = models.Version.get_by_version(version) or\
                    models.Version.add(version, equation)
                package = models.Package.add(req['name'], version)
            packages.append(package)

        return packages

    def buildout_view(self):
        """Return a buildout specified by buildout_id."""
        buildout_id = self.request.matchdict['buildout_id']
        buildout = models.DBSession.query(models.Buildout).filter_by(
           id=int(buildout_id)).one()

        if 'delete' in self.request.params:
            if 'allrevisions' in self.request.params:
                for b in models.Buildout.get_by_name_host(buildout.name, buildout.host).all():
                    models.DBSession.delete(b)
            else:
                models.DBSession.delete(buildout)

            return HTTPFound(location=self.request.route_url('buildouts'))

        if 'checknewversions' in self.request.params:
            for (name, version) in buildout.checknewversions():
                package = models.Package.get_by_nameversion(name, version)
                if not package:
                    version = models.Version.get_by_version(version) or\
                        models.Version.add(version, None)
                    package = models.Package.add(name, version)

        new_buildouts = models.DBSession.query(models.Buildout).\
            join(models.Buildout.host).\
            filter(models.Buildout.host == buildout.host,
                   models.Buildout.name == buildout.name,
                   models.Buildout.id != buildout_id,
                   models.Buildout.datetime > buildout.datetime).\
            order_by(models.Buildout.datetime).all()

        older_buildouts = models.DBSession.query(models.Buildout).join(models.Buildout.host).\
            filter(models.Buildout.host == buildout.host,
                   models.Buildout.name == buildout.name,
                   models.Buildout.datetime < buildout.datetime,
                   models.Buildout.id != buildout_id).\
            order_by(models.Buildout.datetime).all()

        return {'buildout': buildout, 'main': self.main, 'config': buildout.config_dict,
                'older_buildouts': older_buildouts,
                'new_buildouts': new_buildouts}

