# -*- coding: utf-8 -*-
{
    'name': 'Nros. Remito en Facturas de Venta',
    'version': '10.0.1.1',
    'summary': 'El app agrega el vínculo entre Facturas de Ventas y Remitos',
    'author': 'Moogah',
    'website': 'http://www.moogah.com',
    'depends': [
        'sale_stock',
        'vitt_arg_einvoice_format',
        'vitt_official_stock_sequence'
    ],
    'data': [
        'views/stock_view.xml',
        'views/account_invoice_view.xml',
        'views/invoice_template.xml',
    ],
    'installable': True,
}
