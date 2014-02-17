import os

from whiskers import models

from .base import UnitTestBase

path = os.path.dirname(os.path.realpath(__file__))


def _registerRoutes(config):
    config.add_static_view('static', 'whiskers:static', cache_max_age=3600)
    config.add_route('home', '/')


class HostModelTests(UnitTestBase):

    def _getTargetClass(self):
        from whiskers.models import Host
        return Host

    def _makeOne(self, name='latitude', ipv4='127.0.0.1'):
        return self._getTargetClass()(name, ipv4)

    def test_constructor(self):
        instance = self._makeOne()
        self.assertEqual(instance.name, 'latitude')


class VersionModelTests(UnitTestBase):

    def _getTargetClass(self):
        from whiskers.models import Version
        return Version

    def _makeOne(self, version='1.0'):
        return self._getTargetClass()(version)

    def test_constructor(self):
        instance = self._makeOne()
        self.assertEqual(instance.version, '1.0')


class PackageModelTests(UnitTestBase):

    def _getTargetClass(self):
        from whiskers.models import Package
        return Package

    def _makeOne(self, name='package', version='1.0', requires=None):
        from whiskers.models import Version
        return self._getTargetClass()(name, Version(version), requires)

    def _makeTwo(self, name='package', version='1.0'):
        p1 = self._makeOne()
        p2 = self._makeOne(name='package2', requires=[p1])
        return [p1, p2]

    def test_constructor(self):
        instance = self._makeOne()
        self.assertEqual(instance.name, 'package')
        self.assertEqual(instance.version.version, '1.0')

    def test_requires(self):
        instances = self._makeTwo()
        self.assertEqual(instances[0], instances[1].requires[0])


class BuildoutModelTests(UnitTestBase):

    def _getTargetClass(self):
        from whiskers.models import Buildout
        return Buildout

    def _makeOne(self, name='buildout'):
        from whiskers.models import Host
        host = Host('localhost', '127.0.0.1')
        return self._getTargetClass()(name, host, 1234)

    def _makeOneWithPackages(self, name, packages):
        from whiskers.models import Host
        host = Host('localhost', '127.0.0.1')
        return self._getTargetClass()(name, host, 1234, packages=packages)

    def _makePackage(self, name, version):
        from whiskers.models import Package, Version
        version = Version(version)
        return Package(name, version)

    def test_constructor(self):
        instance = self._makeOne()
        self.assertEqual(instance.name, 'buildout')
        self.assertEqual(instance.host.name, 'localhost')

    def test_constructor_with_packages(self):
        p1 = self._makePackage('package-1', '1.0')
        p2 = self._makePackage('package-2', '2.0')
        p3 = self._makePackage('package-3', '3.0')
        p4 = self._makePackage('package-4', '4.0')
        p4.requires = [p3]
        instance = self._makeOneWithPackages(name='buildout',
                                             packages=[p1, p2, p4])
        self.assertEqual(instance.name, 'buildout')
        self.assertEqual(len(instance.packages), 3)
        self.assertEqual(instance.packages[0].name, 'package-1')
        self.assertEqual(instance.packages[0].version.version, '1.0')
        self.assertEqual(instance.packages[1].version.version, '2.0')
        self.assertEqual(instance.packages[2].version.version, '4.0')
        self.assertEqual(instance.packages[2].requires[0], p3)


from random import randint

class InitializeSqlTests(UnitTestBase):

    def _makeHost(self, name='localhost', ip='127.0.0.1'):
        h = models.Host(name, ip)
        models.DBSession.add(h)
        return h

    def _makeBuildout(self, name, host):
        b = models.Buildout(name, host, randint(0,999999))
        models.DBSession.add(b)
        return b

    def _makePackage(self, name, version):
        version = models.Version(version)
        p = models.Package(name, version)
        models.DBSession.add(p)
        return p

    def _createDummyContent(self, session):
        host = models.Host('localhost', '127.0.0.1')
        version = models.Version('1.0')
        package = models.Package('req-package-1', version)
        packages = [models.Package('package1', version),
                    models.Package('package2', models.Version('2.0'),
                            requires=[package])]
        buildout = models.Buildout('buildout', host, 12345, packages=packages)
        session.add(buildout)
        for p in packages:
            session.add(p)
        session.flush()

    def test_it(self):
        self._createDummyContent(models.DBSession)
        buildout = models.DBSession.query(models.Buildout).one()
        self.assertEqual(buildout.name, 'buildout')
        packages = ['package1', 'package2']
        versions = ['1.0', '2.0']
        buildout_packages = [i.name for i in buildout.packages]
        buildout_versions = [i.version.version for i in buildout.packages]

        self.assertEqual(packages.sort(), buildout_packages.sort())
        self.assertEqual(versions.sort(), buildout_versions.sort())
        p1 = models.DBSession.query(models.Package).filter(models.Package.name == 'package2').one()
        self.assertEqual(p1.requires[0].name, 'req-package-1')
        self.assertEqual(buildout.host.name, 'localhost')

    def test_newest_buildouts(self):
        h1 = self._makeHost('server2', '10.0.0.1')
        h2 = self._makeHost('server1', '10.0.0.2')

        b1_h1_v1 = self._makeBuildout('buildout1', h1)
        b1_h1_v2 = self._makeBuildout('buildout1', h1)
        b1_h1_v3 = self._makeBuildout('buildout1', h1)
        b1_h1_v4 = self._makeBuildout('buildout1', h1)
        b2_h1_v1 = self._makeBuildout('buildout2', h1)
        b2_h1_v2 = self._makeBuildout('buildout2', h1)
        b1_h2_v1 = self._makeBuildout('buildout1', h2)
        b1_h2_v2 = self._makeBuildout('buildout1', h2)

        self.assertEqual(b1_h1_v1.getNewestOnTheSameHost(), b1_h1_v4)
        self.assertEqual(b1_h1_v4.getNewestOnTheSameHost(), b1_h1_v4)
        self.assertEqual(b1_h1_v1.isNewestOnTheSameHost(), False)
        self.assertEqual(b1_h1_v4.isNewestOnTheSameHost(), True)

        self.assertEqual(b1_h1_v1.getNewest(), b1_h2_v2)
        self.assertEqual(b1_h2_v2.getNewest(), b1_h2_v2)
        self.assertEqual(b1_h1_v1.isNewest(), False)
        self.assertEqual(b1_h2_v2.isNewest(), True)

        self.assertEqual(b1_h1_v1.hostsWithThisBuildout(), set([h1, h2]))

    def test_newest_package(self):
        p1 = self._makePackage('package', '1.0')
        p2 = self._makePackage('package', '2.0')
        p3 = self._makePackage('package', '3.0')
        p4 = self._makePackage('package', '4.0')

        self.assertEqual(len(models.Package.get_packages_by_name('package').all()), 4)

        self.assertEqual(p1.isNewest(), False)
        self.assertEqual(p2.isNewest(), False)
        self.assertEqual(p3.isNewest(), False)
        self.assertEqual(p4.isNewest(), True)

        self.assertEqual(models.Package.get_newest_by_name('package').version.version, '4.0')

    def test_new_version(self):
        p = self._makePackage('whiskers', '0.1')

        self.assertEqual(models.AllPackagesChecker().check(level=0), [('whiskers', '0.2')])
        self.assertEqual(models.AllPackagesChecker(only_final_versions=False).check(level=0), [('whiskers', '1.0-alpha.3')])


