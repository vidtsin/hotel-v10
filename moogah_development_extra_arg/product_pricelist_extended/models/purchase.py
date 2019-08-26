# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    update_product_cost = fields.Boolean("Update product cost", default=True)

    @api.multi
    def button_confirm(self):
        """ Before call function of super class, is updated

        :return: super(PurchaseOrderPle, self).button_confirm()
        """
        for record in self:
            if record.update_product_cost:
                check_dic = {}
                lines = record.order_line.sorted(key=lambda r: r.sequence)
                for line in lines:
                    check_dic[line.product_id.id] = (line.product_id,
                                                     line.price_unit)
                for value in check_dic.itervalues():
                    product, price_unit = value
                    if product.update_last_po_cost:
                        currency_from = record.currency_id
                        currency_to = product.product_currency_id
                        context = {'date': record.date_order}
                        product.last_po_cost = currency_from.with_context(
                            context).compute(price_unit, currency_to)
        return super(PurchaseOrder, self).button_confirm()
