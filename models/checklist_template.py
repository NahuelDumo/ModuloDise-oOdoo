# design.checklist_template.py

from odoo import models, fields

class ChecklistTemplate(models.Model):
    _name = "design.checklist_template"
    _description = "Plantilla de Checklist"

    name = fields.Char("Nombre de la plantilla", required=True)
    
    # Cambiamos selección por relación
    categoria_id = fields.Many2one(
        "product.category", string="Categoría de producto", required=True
    )

    etapa = fields.Selection([
        ('etapa1', 'Etapa 1'),
        ('etapa2', 'Etapa 2')
    ], string="Etapa", required=True)

    item_ids = fields.One2many("design.checklist_template_item", "template_id", string="Items de la plantilla")
