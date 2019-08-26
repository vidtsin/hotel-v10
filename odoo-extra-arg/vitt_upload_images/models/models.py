# -*- coding: utf-8 -*-
from odoo import http, models, fields, api, _
import requests
import base64

class ProductsImages(models.Model):
    _name = 'products.images'

    name = fields.Char(string="Nombre")
    url = fields.Char(string="URL")
    extid = fields.Char()
    done = fields.Boolean(string="Done")

    def is_number(self,s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def uplodad_images(self):
        pimgs = self.env['products.images'].search([])

        for pimg in pimgs:
            ids = pimg.extid.split("_")
            if self.is_number(ids[-1]):
                id = int(ids[-1])
                prods = self.env['product.template'].search([('id','=',id)])
                if prods:
                    f = open('./image', 'wb')
                    f.write(requests.get(pimg.url).content)
                    f.close()

                    file = open("./image", "r")
                    res = file.read()
                    res = base64.encodestring(res)
                    file.close()
                    try:
                        prods.write({'image_medium':res})
                        pimg.write({'done':True})
                    except:
                        pass