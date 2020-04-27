import cherrypy

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import AccessType, SortDir, TokenScope

from codes.models.code import Code as CodeModel


class Code(Resource):

    def __init__(self):
        super(Code, self).__init__()
        self.resourceName = 'codes'
        self.route('GET', (), self.find)
        self.route('POST', (), self.create)
        self.route('GET', (':id', ), self.find_id)
        self.route('DELETE', (':id', ), self.remove)
        self.route('DELETE', (), self.remove_all)

    def _clean(self, doc):
        del doc['access']
        doc['_id'] = str(doc['_id'])
        return doc

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Find code')
        .param('name', 'Code name', required=False)
        .param('url', 'Organization Url', required=False)
        .param('github', 'GitHub repo', required=False)
        .param('description', 'Description of the code', required=False)
        .param('docker', 'Docker repository', required=False)
        .pagingParams(defaultSort='_id',
                      defaultSortDir=SortDir.DESCENDING,
                      defaultLimit=25)
    )
    def find(self, **kwargs):
        return CodeModel().find_codes(kwargs, user=self.getCurrentUser())

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a code.')
        .param('name', 'Code name')
        .param('url', 'Organization Url', required=False)
        .param('github', 'GitHub repo', required=False)
        .param('description', 'Description of the code', required=False)
        .param('docker', 'Docker repository', required=False)
    )
    def create(self, **kwargs):
        code = CodeModel().create(kwargs, user=self.getCurrentUser())
        cherrypy.response.status = 201
        return self._clean(code)

    @access.user(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Fetch a code.')
        .modelParam('id', 'The code id',
                    model=CodeModel, destName='code',
                    level=AccessType.READ, paramType='path')
    )
    def find_id(self, code):
        return self._clean(code)

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Delete a code.')
        .modelParam('id', 'The code id',
                    model=CodeModel, destName='code',
                    level=AccessType.WRITE, paramType='path')
    )
    def remove(self, code):
        CodeModel().remove(code)
        cherrypy.response.status = 204
        return

    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Remove all codes the user has permissions to remove.')
    )
    def remove_all(self):
        CodeModel().remove_all(self.getCurrentUser())
        cherrypy.response.status = 204
        return
