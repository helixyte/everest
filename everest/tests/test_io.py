"""
This file is part of the everest project.
See LICENSE.txt for licensing, CONTRIBUTORS.txt for contributor information.

Created on Feb 21, 2012.
"""
import glob
import os
import shutil
import tempfile
import zipfile

from pyramid.compat import NativeIO
from pyramid.compat import itervalues_

from everest.compat import BytesIO
from everest.mime import CsvMime
from everest.repositories.rdb.testing import RdbTestCaseMixin
from everest.representers.config import IGNORE_OPTION
from everest.resources.staging import create_staging_collection
from everest.resources.storing import ConnectedResourcesSerializer
from everest.resources.storing import build_resource_dependency_graph
from everest.resources.storing import dump_resource
from everest.resources.storing import dump_resource_to_files
from everest.resources.storing import dump_resource_to_zipfile
from everest.resources.storing import find_connected_resources
from everest.resources.storing import get_collection_filename
from everest.resources.storing import get_collection_name
from everest.resources.storing import load_collection_from_file
from everest.resources.storing import load_collection_from_stream
from everest.resources.storing import load_collection_from_url
from everest.resources.storing import load_into_collection_from_url
from everest.resources.storing import load_into_collections_from_zipfile
from everest.resources.utils import get_collection_class
from everest.resources.utils import get_member_class
from everest.resources.utils import get_root_collection
from everest.testing import ResourceTestCase
from everest.tests.complete_app.entities import MyEntity
from everest.tests.complete_app.entities import MyEntityChild
from everest.tests.complete_app.entities import MyEntityGrandchild
from everest.tests.complete_app.entities import MyEntityParent
from everest.tests.complete_app.interfaces import IMyEntity
from everest.tests.complete_app.interfaces import IMyEntityChild
from everest.tests.complete_app.interfaces import IMyEntityGrandchild
from everest.tests.complete_app.interfaces import IMyEntityParent


__docformat__ = 'reStructuredText en'
__all__ = ['ConnectedResourcesTestCase',
           'FileResourceIoTestCase',
           'ResourceDependencyGraphTestCase',
           'ResourceGraphTestCase',
           'StreamResourceIoTestCase',
           'ZipResourceIoTestCaseNoRdb',
           'ZipResourceIoTestCaseRdb',
           ]


def _make_test_entity_member():
    parent = MyEntityParent()
    entity = MyEntity(parent=parent)
    if parent.child is None:
        parent.child = entity
    child = MyEntityChild()
    entity.children.append(child)
    if child.parent is None:
        child.parent = entity
    grandchild = MyEntityGrandchild()
    child.children.append(grandchild)
    if grandchild.parent is None:
        grandchild.parent = child
    coll = create_staging_collection(IMyEntity)
    mb = coll.create_member(entity)
    parent.id = 0
    entity.id = 0
    child.id = 0
    grandchild.id = 0
    return mb


class ResourceGraphTestCase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'
    config_file_name = 'configure_no_rdb.zcml'
    _interfaces = [IMyEntityParent, IMyEntity, IMyEntityChild,
                   IMyEntityGrandchild]


class ResourceDependencyGraphTestCase(ResourceGraphTestCase):

    def test_dependency_graph(self):
        grph = build_resource_dependency_graph(self._interfaces)
        self.assert_equal(len(grph.nodes()), 4)
        entity_mb_cls = get_member_class(IMyEntity)
        entity_parent_mb_cls = get_member_class(IMyEntityParent)
        entity_child_mb_cls = get_member_class(IMyEntityChild)
        entity_grandchild_mb_cls = get_member_class(IMyEntityGrandchild)
        # Entity Parent resource deps should be empty.
        self.assert_equal(grph.neighbors(entity_parent_mb_cls), [])
        # Entity Child has Grandchild.
        self.assert_equal(grph.neighbors(entity_child_mb_cls),
                          [entity_grandchild_mb_cls])
        # Entity Grandchild has Child, but backrefs are excluded by default.
        self.assert_equal(grph.neighbors(entity_grandchild_mb_cls),
                          [])
        # Entity has Parent and Child.
        self.assert_equal(set(grph.neighbors(entity_mb_cls)),
                          set([entity_parent_mb_cls, entity_child_mb_cls]))


class ConnectedResourcesTestCase(ResourceGraphTestCase):

    def test_find_connected_with_member(self):
        member = _make_test_entity_member()
        ent_map = find_connected_resources(member)
        for ents in itervalues_(ent_map):
            self.assert_equal(len(ents), 1)

    def test_find_connected_with_collection(self):
        member = _make_test_entity_member()
        ent_map = find_connected_resources(member.__parent__)
        for ents in itervalues_(ent_map):
            self.assert_equal(len(ents), 1)

    def test_find_connected_with_deps(self):
        member = _make_test_entity_member()
        dep_grph = \
            build_resource_dependency_graph(self._interfaces,
                                            include_backrefs=True)
        ent_map = find_connected_resources(member,
                                            dependency_graph=dep_grph)
        # Backrefs should not make a difference since we check for duplicates.
        for ents in itervalues_(ent_map):
            self.assert_equal(len(ents), 1)

    def test_convert_to_strings(self):
        member = _make_test_entity_member()
        srl = ConnectedResourcesSerializer(CsvMime)
        rpr_map = srl.to_strings(member)
        self.assert_equal(len(rpr_map), 4)


class _ResourceIoTestCaseBase(ResourceTestCase):
    package_name = 'everest.tests.complete_app'

    def set_up(self):
        ResourceTestCase.set_up(self)
        # We need to switch off non-standard resource attributes manually.
        self.config.add_resource_representer(
                    IMyEntity, CsvMime,
                    attribute_options=
                            {('children',):{IGNORE_OPTION:True}
                             })


class _ZipResourceIoTestCaseBase(_ResourceIoTestCaseBase):

    def test_load_from_zipfile(self):
        member = _make_test_entity_member()
        strm = BytesIO()
        dump_resource_to_zipfile(member, strm)
        colls = [
                 get_root_collection(IMyEntityParent),
                 get_root_collection(IMyEntity),
                 get_root_collection(IMyEntityChild),
                 get_root_collection(IMyEntityGrandchild),
                 ]
        self.assert_equal(len(colls[0]), 0)
        self.assert_equal(len(colls[1]), 0)
        self.assert_equal(len(colls[2]), 0)
        self.assert_equal(len(colls[3]), 0)
        load_into_collections_from_zipfile(colls, strm)
        self.assert_equal(len(colls[0]), 1)
        self.assert_equal(len(colls[1]), 1)
        self.assert_equal(len(colls[2]), 1)
        self.assert_equal(len(colls[3]), 1)


class ZipResourceIoTestCaseNoRdb(_ZipResourceIoTestCaseBase):
    config_file_name = 'configure_no_rdb.zcml'

    def test_load_from_zipfile_invalid_extension(self):
        strm = BytesIO()
        zipf = zipfile.ZipFile(strm, 'w')
        coll_name = get_collection_name(get_collection_class(IMyEntity))
        zipf.writestr('%s.foo' % coll_name, '')
        zipf.close()
        colls = [get_root_collection(IMyEntity)]
        with self.assert_raises(ValueError) as cm:
            load_into_collections_from_zipfile(colls, strm)
        exc_msg = 'Could not infer MIME type'
        self.assert_true(str(cm.exception).startswith(exc_msg))

    def test_load_from_zipfile_filename_not_found(self):
        strm = BytesIO()
        zipf = zipfile.ZipFile(strm, 'w')
        zipf.writestr('foo.foo', '')
        zipf.close()
        colls = [get_root_collection(IMyEntity)]
        load_into_collections_from_zipfile(colls, strm)
        self.assert_equal(len(colls[0]), 0)


class ZipResourceIoTestCaseRdb(RdbTestCaseMixin, _ZipResourceIoTestCaseBase):
    config_file_name = 'configure.zcml'


class StreamResourceIoTestCase(_ResourceIoTestCaseBase):
    config_file_name = 'configure_no_rdb.zcml'
    def test_dump_no_content_type(self):
        member = _make_test_entity_member()
        strm = NativeIO()
        dump_resource(member, strm)
        self.assert_true(strm.getvalue().startswith('"id",'))


class FileResourceIoTestCase(_ResourceIoTestCaseBase):
    config_file_name = 'configure_no_rdb.zcml'
    def _test_load(self, load_func, fn_func, is_into):
        member = _make_test_entity_member()
        tmp_dir = tempfile.mkdtemp()
        try:
            dump_resource_to_files(member, directory=tmp_dir)
            file_names = glob.glob1(tmp_dir, "*.csv")
            self.assert_equal(len(file_names), 4)
            for ifc in [IMyEntityParent,
                        IMyEntity,
                        IMyEntityChild,
                        IMyEntityGrandchild]:
                coll_cls = get_collection_class(ifc)
                root_coll = get_root_collection(ifc)
                file_name = get_collection_filename(coll_cls)
                file_path = fn_func(os.path.join(tmp_dir, file_name))
                if not is_into:
                    coll = load_func(coll_cls, file_path)
                    self.assert_equal(len(coll), 1)
                    for mb in coll:
                        root_coll.add(mb)
                else:
                    load_func(root_coll, file_path)
                    self.assert_equal(len(root_coll), 1)
        finally:
            shutil.rmtree(tmp_dir)

    def test_load_from_invalid_file(self):
        coll_cls = get_collection_class(IMyEntity)
        with self.assert_raises(ValueError) as cm:
            dummy = \
              load_collection_from_file(coll_cls, 'my-entity-collection.foo')
        exc_msg = 'Could not infer MIME type'
        self.assert_true(str(cm.exception).startswith(exc_msg))

    def test_load_from_file(self):
        self._test_load(load_collection_from_file, lambda fn: fn, False)

    def test_load_from_stream(self):
        self._test_load(lambda rc, fn: load_collection_from_stream(rc, fn,
                                                                   CsvMime),
                        lambda fn: open(fn, 'rU'), False)

    def test_load_from_file_url(self):
        self._test_load(load_collection_from_url,
                        lambda fn: "file://%s" % fn, False)

    def test_load_from_file_url_into(self):
        self._test_load(load_into_collection_from_url,
                        lambda fn: "file://%s" % fn, True)

    def test_load_from_invalid_file_url(self):
        self.assert_raises(ValueError,
                           self._test_load,
                           load_collection_from_url,
                           lambda fn: "http://%s" % fn, False)
