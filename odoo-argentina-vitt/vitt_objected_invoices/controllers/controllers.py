# -*- coding: utf-8 -*-
from odoo import http

# class ./extra-addonsTmp/vittar/vittObjectedInvoices(http.Controller):
#     @http.route('/./extra-addons_tmp/vittar/vitt_objected_invoices/./extra-addons_tmp/vittar/vitt_objected_invoices/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/./extra-addons_tmp/vittar/vitt_objected_invoices/./extra-addons_tmp/vittar/vitt_objected_invoices/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('./extra-addons_tmp/vittar/vitt_objected_invoices.listing', {
#             'root': '/./extra-addons_tmp/vittar/vitt_objected_invoices/./extra-addons_tmp/vittar/vitt_objected_invoices',
#             'objects': http.request.env['./extra-addons_tmp/vittar/vitt_objected_invoices../extra-addons_tmp/vittar/vitt_objected_invoices'].search([]),
#         })

#     @http.route('/./extra-addons_tmp/vittar/vitt_objected_invoices/./extra-addons_tmp/vittar/vitt_objected_invoices/objects/<model("./extra-addons_tmp/vittar/vitt_objected_invoices../extra-addons_tmp/vittar/vitt_objected_invoices"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('./extra-addons_tmp/vittar/vitt_objected_invoices.object', {
#             'object': obj
#         })