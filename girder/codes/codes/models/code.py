from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel

from codes.utils.pagination import parse_pagination_params
from codes.utils.pagination import search_results_dict


class Code(AccessControlledModel):

    def initialize(self):
        self.name = 'codes'

    def validate(self, doc):
        if 'name' not in doc:
            raise ValidationException('Code must be given a name')

        query = {'name': doc['name']}
        if self.collection.count_documents(query) != 0:
            raise ValidationException('An identical code already exists')

        return doc

    def find_codes(self, params=None, user=None):
        if params is None:
            params = {}

        limit, offset, sort = parse_pagination_params(params)

        # This is for query fields that can just be copied over directly
        query_fields = ['name', 'url', 'github', 'description', 'docker']
        query_fields = [x for x in query_fields if params.get(x) is not None]
        query = {x: params[x] for x in query_fields}

        # This is for the returned fields
        fields = ['name', 'url', 'github', 'description', 'docker']
        cursor = self.findWithPermissions(query, fields=fields, limit=limit,
                                          offset=offset, sort=sort, user=user)

        num_matches = cursor.collection.count_documents(query)

        codes = [x for x in cursor]
        return search_results_dict(codes, num_matches, limit, offset, sort)

    def create(self, params, user):
        # These are the fields we want to copy over
        fields = ['name', 'url', 'github', 'description', 'docker']
        code = {key: params[key] for key in fields if key in params}

        self.setUserAccess(code, user=user, level=AccessType.ADMIN)

        # These are always public currently
        self.setPublic(code, True)

        return self.save(code)

    def remove_all(self, user):
        cursor = self.findWithPermissions({}, fields=[], user=user,
                                          level=AccessType.ADMIN)
        for code in cursor:
            self.remove(code)
