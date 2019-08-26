# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def pack_operation_ids_cons(self,doc):
        res = []
        for reg in doc.pack_operation_ids:
            if not reg.product_id.name in res:
                res.append(reg.product_id.name)
        return res

    def pack_operation_ord(self,doc,item):
        tot = 0.0
        for reg in doc.pack_operation_ids:
            if reg.product_id.name in item:
                tot += reg.ordered_qty
        return tot

    def pack_operation_real(self,doc,item):
        tot = 0.0
        for reg in doc.pack_operation_ids:
            if reg.product_id.name in item:
                tot += reg.qty_done
        return tot
