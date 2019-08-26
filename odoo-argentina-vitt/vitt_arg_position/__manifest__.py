# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com)

{
    'name': 'Argentina - Posiciones Fiscales',
    'version': '10.0.1.4',
    'description': """
Template de Posiciones Fiscales con reemplazo de cod. IVA e identificación por tipo de responsabilidad.
Considera Operaciones Exentas, No Gravadas y reemplazo de impuestos para Monotributistas y Consumidor Final

    """,
    'author': ['Moogah'],
    'website': 'http://www.moogah.com',
    'category': 'Localization',
    'depends': ['account'],
    'data':[
        'data/f_position_arg_data.xml',
    ],
}