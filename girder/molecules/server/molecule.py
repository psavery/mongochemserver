import cherrypy
import json
import os
import functools

from girder.api.describe import Description
from girder.api.docs import addModel
from girder.api.rest import Resource
from girder.api.rest import RestException
from girder.api import access
from girder.constants import AccessType
from . import avogadro
from . import openbabel

class Molecule(Resource):
    output_formats = ['cml', 'xyz', 'inchikey', 'sdf']
    input_formats = ['cml', 'xyz', 'sdf', 'cjson', 'pdb']

    def __init__(self):
        self.resourceName = 'molecules'
        self.route('GET', (), self.find)
        self.route('GET', ('inchikey', ':inchikey'), self.find_inchikey)
        self.route('POST', (), self.create)
        self.route('DELETE', (':id',), self.delete)
        self.route('PATCH', (':id',), self.update)
        self.route('POST', ('conversions', ':output_format'), self.conversions)

        self._model = self.model('molecule', 'molecules')

    def _clean(self, doc):
        del doc['access']
        doc['_id'] = str(doc['_id'])

        return doc

    @access.public
    def find(self, params):
        return self._model.findmol()
    find.description = (
            Description('Find a molecule.')
            .param('inchi', 'The InChI of the molecule', paramType='query',
                   required=False)
            .errorResponse())

    @access.public
    def find_inchikey(self, inchikey, params):
        mol = self._model.find_inchikey(inchikey)
        if not mol:
            raise RestException('Molecule not found.', code=404)
        return self._clean(mol)
    find_inchikey.description = (
            Description('Find a molecule by InChI key.')
            .param('inchi', 'The InChI key of the molecule', paramType='path')
            .errorResponse()
           .errorResponse('Molecule not found.', 404))

    @access.user
    def create(self, params):
        body = self.getBodyJson()
        user = self.getCurrentUser()

        if 'fileId' in body:
            file_id = body['fileId']
            file = self.model('file').load(file_id, user=user)
            parts = file['name'].split('.')
            input_format = parts[-1]
            name = '.'.join(parts[:-1])

            if input_format not in Molecule.input_formats:
                raise RestException('Input format not supported.', code=400)

            contents = functools.reduce(lambda x, y: x + y, self.model('file').download(file, headers=False)())
            data_str = contents.decode()

            # Use the SDF format as it is the one with bonding that 3Dmol uses.
            output_format = 'sdf'

            if output_format == 'pdb':
                (output, _) = openbabel.convert_str(data_str, input_format, output_format)
            else:
                output = avogadro.convert_str(data_str, input_format, output_format)

            cjson = json.loads(avogadro.convert_str(output, 'sdf', 'cjson'))
            print(cjson)

            atom_count = openbabel.atom_count(data_str, input_format)

            if atom_count > 1024:
                raise RestException('Unable to generate inchi, molecule has more than 1024 atoms .', code=400)

            (inchi, inchikey) = openbabel.to_inchi(output, 'sdf')

            if not inchi:
                raise RestException('Unable to extract inchi', code=400)

            mol = self._model.create_xyz(user, {
                'name': name, # For now
                'inchi': inchi,
                'inchikey': inchikey,
                output_format: output,
                'cjson': cjson
            })

        elif 'xyz' in body or 'sdf' in body:

            if 'xyz' in body:
                input_format = 'xyz'
                data = body['xyz']
            else:
                input_format = 'sdf'
                data = body['sdf']

            (inchi, inchikey) = openbabel.to_inchi(data, input_format)

            mol = {
                'inchi': inchi,
                'inchikey': inchikey,
                input_format: data
            }

            if 'name' in body:
                mol['name'] = body['name']

            mol = self._model.create_xyz(user, mol)
        elif 'inchi' in body:
            inchi = body['inchi']
            mol = self._model.create(user, inchi)
        else:
            raise RestException('Invalid request', code=400)

        return self._clean(mol)

    addModel('MoleculeParams', {
        "id": "MoleculeParams",
        "required": ["name", "inchi"],
        "properties": {
            "name": {"type": "string", "description": "The common name of the molecule"},
            "inchi": {"type": "string", "description": "The InChI of the molecule."}
        }
    })
    create.description = (
        Description('Create a molecule')
        .param(
            'body',
            'The molecule to be added to the database.',
            dataType='MoleculeParams',
            required=True, paramType='body')
        .errorResponse('Input format not supported.', code=400))

    @access.user
    def delete(self, id, params):
        user = self.getCurrentUser()
        mol = self._model.load(id, user=user, level=AccessType.WRITE)

        if not mol:
            raise RestException('Molecule not found.', code=404)

        return self._model.remove(mol)

    delete.description = (
            Description('Delete a molecule by id.')
            .param('id', 'The id of the molecule', paramType='path')
            .errorResponse()
            .errorResponse('Molecule not found.', 404))

    @access.user
    def update(self, id, params):
        user = self.getCurrentUser()

        mol = self._model.load(id, user=user, level=AccessType.WRITE)

        if not mol:
            raise RestException('Molecule not found.', code=404)

        body = self.getBodyJson()

        if 'logs' in body:
            logs = mol.setdefault('logs', [])
            logs += body['logs']

        mol = self._model.update(mol)

        return self._clean(mol)
    addModel('UpdateMoleculeParams', {
        "id": "UpdateMoleculeParams",
        "properties": {
            "logs": {"type": "array", "description": "List of Girder file ids"}
        }
    })
    update.description = (
            Description('Update a molecule by id.')
            .param('id', 'The id of the molecule', paramType='path')
            .param(
            'body',
            'The update to the molecule.',
            dataType='UpdateMoleculeParams',
            required=True, paramType='body')
            .errorResponse('Molecule not found.', 404))

    @access.user
    def conversions(self, output_format, params):
        user = self.getCurrentUser()

        if output_format not in Molecule.output_formats:
            raise RestException('Output output_format not supported.', code=404)

        body = self.getBodyJson()

        if 'fileId' not in body:
            raise RestException('Invalid request body.', code=400)

        file_id = body['fileId']

        file = self.model('file').load(file_id, user=user)

        input_format = file['name'].split('.')[-1]

        if input_format not in Molecule.input_formats:
            raise RestException('Input format not supported.', code=400)

        if file is None:
            raise RestException('File not found.', code=404)

        contents = functools.reduce(lambda x, y: x + y, self.model('file').download(file, headers=False)())
        data_str = contents.decode()

        if output_format.startswith('inchi'):
            atom_count = 0
            if input_format == 'pdb':
                atom_count = openbabel.atom_count(data_str, input_format)
            else:
                atom_count = avogadro.atom_count(data_str, input_format)

            if atom_count > 1024:
                raise RestException('Unable to generate InChI, molecule has more than 1024 atoms.', code=400)

            if input_format == 'pdb':
                (inchi, inchikey) = openbabel.to_inchi(data_str, input_format)
            else:
                sdf = avogadro.convert_str(data_str, input_format, 'sdf')
                (inchi, inchikey) = openbabel.to_inchi(sdf, 'sdf')

            if output_format == 'inchi':
                return inchi
            else:
                return inchikey

        else:
            output = ''
            mime = 'text/plain'
            if input_format == 'pdb':
                (output, mime) = openbabel.convert_str(data_str, input_format, output_format)
            else:
                output = avogadro.convert_str(data_str, input_format, output_format)

            def stream():
                cherrypy.response.headers['Content-Type'] = mime
                yield output

            return stream

    addModel('ConversionParams', {
        "id": "ConversionParams",
        "properties": {
            "fileId": {"type": "string", "description": "Girder file id to do conversion on"}
        }
    })
    conversions.description = (
            Description('Update a molecule by id.')
            .param('format', 'The format to convert to', paramType='path')
            .param(
            'body',
            'Details of molecule data to perform conversion on',
            dataType='ConversionParams',
            required=True, paramType='body')
            .errorResponse('Output format not supported.', 404)
            .errorResponse('File not found.', 404)
            .errorResponse('Invalid request body.', 400)
            .errorResponse('Input format not supported.', code=400))
