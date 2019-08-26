# -*- coding: utf-8 -*-
# 2018 Moogah

from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def get_vatincluded(self):
        comp_type = self.company_id.afip_responsability_type_id
        partner_type = self.partner_id.afip_responsability_type_id

        if not partner_type:
           return False
        else:
            for type in comp_type.issued_letter_ids:
                for rec in type.receptor_ids:
                    if partner_type.name == rec.name:
                        for issue in type.issuer_ids:
                            if comp_type.name == issue.name:
                                if type.taxes_included:
                                    return True
                                else:
                                    return False

            return False

    def get_value(self,amount,line):
        tmp = 0.0
        if self.get_vatincluded():
            for tax in line.tax_id:
                if tax.amount > 0:
                    tmp += tax.amount * amount / 100
            return tmp + amount
        else:
            return amount