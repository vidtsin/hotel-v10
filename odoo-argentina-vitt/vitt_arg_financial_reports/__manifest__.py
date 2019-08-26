# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com)

{
    'name': 'Argentina - Financial Reports',
    'version': '10.0.1.1',
    'description': """
Definición de Reportes Financieros en base al Plan de Cuentas ARG de Moogah. Se utilizan "Etiquetas de Cuentas" en lugar de Tipos de Cuentas para estos informes.
Los informes se muestran disponibles desde el nuevo sub-menú: Informes Legales Argentina, desde Contabilidad > Informes

    """,
    'author': ['Moogah'],
    'website': 'http://www.moogah.com',
    'category': 'Localization',
    'depends': ['base', 'account'],
    'data':[
        'data/arg_balance_report.xml'
    ],
}
