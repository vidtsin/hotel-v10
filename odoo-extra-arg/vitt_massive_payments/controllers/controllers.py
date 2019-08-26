# -*- coding: utf-8 -*-
from odoo import http

# class VittMassivePayments(http.Controller):
#     @http.route('/vitt_massive_payments/vitt_massive_payments/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/vitt_massive_payments/vitt_massive_payments/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('vitt_massive_payments.listing', {
#             'root': '/vitt_massive_payments/vitt_massive_payments',
#             'objects': http.request.env['vitt_massive_payments.vitt_massive_payments'].search([]),
#         })

#     @http.route('/vitt_massive_payments/vitt_massive_payments/objects/<model("vitt_massive_payments.vitt_massive_payments"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('vitt_massive_payments.object', {
#             'object': obj
#         })