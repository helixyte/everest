from pkg_resources import resource_filename # pylint: disable=E0611

def load_plugin(config):
    config.load_zcml(resource_filename(__package__, 'configure.zcml'))