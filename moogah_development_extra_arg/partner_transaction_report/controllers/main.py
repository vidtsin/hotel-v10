# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import Controller, request
from odoo.addons.web.controllers.main import _serialize_exception
from odoo.tools import html_escape


class FileDispatcher(Controller):
    @http.route('/download_custom_file/', type='http', auth='user')
    def dispatch_file(self, data, token):
        _data = json.loads(data)
        _obj_class = request.env[_data['model']]
        _obj = _obj_class.search([('id', '=', _data['record_id'])])[0]
        try:
            response = request.make_response(_obj.get_file(), headers=[
                ('Content-Type', _obj.get_content_type()),
                ('Content-Disposition', u'attachment; filename=' + _obj.get_filename() + ';')
            ], cookies={
                'fileToken': token
            })
            return response
        except Exception, e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': 'Odoo Server Error',
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))

