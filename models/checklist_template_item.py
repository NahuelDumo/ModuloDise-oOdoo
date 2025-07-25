from odoo import models, fields

class ChecklistTemplateItem(models.Model):
    _name = "design.checklist_template_item"
    _description = "Ítem de plantilla de checklist"
    _order = "orden asc"

    name = fields.Char("Descripción del ítem", required=True)
    template_id = fields.Many2one("design.checklist_template", string="Plantilla", required=True, ondelete="cascade")
    orden = fields.Integer("Orden", default=1)
    comentario_default = fields.Text("Comentario por defecto (opcional)")
