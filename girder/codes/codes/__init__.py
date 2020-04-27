from girder import events
from girder.models.user import User as UserModel
from girder.plugin import GirderPlugin

from codes.code import Code


class CodesPlugin(GirderPlugin):
    DISPLAY_NAME = 'OpenChemistry Codes'

    def load(self, info):
        info['apiRoot'].codes = Code()


def load_defaults(event):
    cluster_id = str(event.info['_id'])

    # Use the first admin user we can find
    users = UserModel().find({'admin': True})
    if users.count() == 0:
        raise Exception('No admin users found. Cannot populate images')

    register_images(users[0], cluster_id)
