# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DesignImage(models.Model):
    _name = 'design.image'
    _description = 'Imagen de Diseño'
    _order = 'sequence, id'
    
    name = fields.Char('Nombre', required=True)
    image = fields.Binary('Imagen', required=True)
    design_id = fields.Many2one('design.design', string='Diseño', ondelete='cascade', required=True)
    sequence = fields.Integer('Secuencia', default=10, help="Define el orden de las imágenes")
    
    # Restricción para asegurar que cada diseño no tenga imágenes duplicadas
    _sql_constraints = [
        ('unique_image_per_design', 'UNIQUE(design_id, image)', '¡No puede haber imágenes duplicadas en un mismo diseño!')
    ]
