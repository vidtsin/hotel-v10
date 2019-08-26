# -*- coding: utf-8 -*-

{
    'name': 'Reporte de Impuestos Internos Compras y Ventas',
    'version': '10.0.1.3',
    'category': 'Hidden/Dependency',
    'depends': ['purchase', 'sale_stock', 'l10n_ar_account', 'report_xls'],
    'description': """
Este app instala el informe que muestra los valores de Impuestos Internos por producto en Facturas de Ventas y Compras, y la diferencia del cálculo al comparar ambos.
===============================================
    """,
    'data': [
        'data/report_paperformat.xml',
        'views/stock_picking_views.xml',
        'wizard/arg_internal_taxes_report_wizard_views.xml',
        'views/report_internal_taxes.xml',
        'views/arg_internal_tax_report.xml',
    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
}
