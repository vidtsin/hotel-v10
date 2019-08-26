# -*- coding: utf-8 -*-
from odoo import http

# class ./extra-addonsTmp/vittar/vittAnalTagsSetting(http.Controller):
#     @http.route('/./extra-addons_tmp/vittar/vitt_anal_tags_setting/./extra-addons_tmp/vittar/vitt_anal_tags_setting/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/./extra-addons_tmp/vittar/vitt_anal_tags_setting/./extra-addons_tmp/vittar/vitt_anal_tags_setting/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('./extra-addons_tmp/vittar/vitt_anal_tags_setting.listing', {
#             'root': '/./extra-addons_tmp/vittar/vitt_anal_tags_setting/./extra-addons_tmp/vittar/vitt_anal_tags_setting',
#             'objects': http.request.env['./extra-addons_tmp/vittar/vitt_anal_tags_setting../extra-addons_tmp/vittar/vitt_anal_tags_setting'].search([]),
#         })

#     @http.route('/./extra-addons_tmp/vittar/vitt_anal_tags_setting/./extra-addons_tmp/vittar/vitt_anal_tags_setting/objects/<model("./extra-addons_tmp/vittar/vitt_anal_tags_setting../extra-addons_tmp/vittar/vitt_anal_tags_setting"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('./extra-addons_tmp/vittar/vitt_anal_tags_setting.object', {
#             'object': obj
#         })