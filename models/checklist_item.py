from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
from datetime import datetime

class ChecklistItem(models.Model):
    _name = "design.checklist_item"
    _description = "Ítem de checklist aplicado a diseño"
    _order = "orden asc"

    name = fields.Char("Descripción", required=True)
    orden = fields.Integer("Orden", default=1)
    design_id = fields.Many2one("design.design", string="Diseño relacionado", ondelete="cascade")

    comentario = fields.Text("Comentario")

    # Validación diseñador
    validado_por_disenador = fields.Boolean("Validado por Diseñador")
    fecha_disenador = fields.Datetime("Fecha validación diseñador", readonly=True)
    usuario_disenador = fields.Many2one("res.users", string="Usuario diseñador", readonly=True)

    # Validación validador
    validado_por_validador = fields.Boolean("Validado por Validador")
    fecha_validador = fields.Datetime("Fecha validación validador", readonly=True)
    usuario_validador = fields.Many2one("res.users", string="Usuario validador", readonly=True)

    # Campos calculados para control de permisos en la vista
    current_user_is_designer = fields.Boolean("Usuario actual es diseñador", 
                                             compute='_compute_user_permissions', 
                                             store=False)
    current_user_is_validator = fields.Boolean("Usuario actual es validador", 
                                              compute='_compute_user_permissions', 
                                              store=False)

    @api.depends('design_id')
    def _compute_user_permissions(self):
        """Calcula los permisos del usuario actual para usar en attrs de la vista"""
        for record in self:
            record.current_user_is_designer = self.env.user.has_group('ModuloDisenoOdoo.group_disenador')
            record.current_user_is_validator = self.env.user.has_group('ModuloDisenoOdoo.group_validador')

    @api.onchange('validado_por_disenador')
    def _onchange_validado_disenador(self):
        """Actualiza fecha y usuario cuando el diseñador valida"""
        if self.validado_por_disenador and not self.usuario_disenador:
            if not self.env.user.has_group('ModuloDisenoOdoo.group_disenador'):
                raise ValidationError(_("Solo los diseñadores pueden validar este campo."))
            self.fecha_disenador = fields.Datetime.now()
            self.usuario_disenador = self.env.user

    @api.onchange('validado_por_validador')
    def _onchange_validado_validador(self):
        """Actualiza fecha y usuario cuando el validador valida"""
        if self.validado_por_validador and not self.usuario_validador:
            if not self.env.user.has_group('ModuloDisenoOdoo.group_validador'):
                raise ValidationError(_("Solo los validadores pueden validar este campo."))
            self.fecha_validador = fields.Datetime.now()
            self.usuario_validador = self.env.user

    def write(self, vals):
        """Control de permisos y registro de cambios"""
        
        # Verificar permisos antes de escribir
        for record in self:
            # Control para validado_por_disenador
            if 'validado_por_disenador' in vals:
                if not self.env.user.has_group('ModuloDisenoOdoo.group_disenador'):
                    raise AccessError(_("Solo los diseñadores pueden marcar items como validados por diseñador."))
                
                # Si se está marcando como validado, actualizar fecha y usuario
                if vals['validado_por_disenador'] and not record.usuario_disenador:
                    vals['fecha_disenador'] = fields.Datetime.now()
                    vals['usuario_disenador'] = self.env.user.id

            # Control para validado_por_validador  
            if 'validado_por_validador' in vals:
                if not self.env.user.has_group('ModuloDisenoOdoo.group_validador'):
                    raise AccessError(_("Solo los validadores pueden marcar items como validados por validador."))
                
                # Si se está marcando como validado, actualizar fecha y usuario
                if vals['validado_por_validador'] and not record.usuario_validador:
                    vals['fecha_validador'] = fields.Datetime.now()
                    vals['usuario_validador'] = self.env.user.id

        # Ejecutar la escritura
        res = super(ChecklistItem, self).write(vals)

        # Registrar en el historial después de la escritura
        for item in self:
            design = item.design_id

            # Registrar validación del diseñador
            if vals.get('validado_por_disenador') and item.usuario_disenador == self.env.user:
                self.env['design.revision_log'].create({
                    'design_id': design.id,
                    'usuario_id': self.env.user.id,
                    'observaciones': f"Ítem validado por diseñador: {item.name}",
                    'tipo': 'validacion_disenador',
                })

            # Registrar validación del validador
            if vals.get('validado_por_validador') and item.usuario_validador == self.env.user:
                self.env['design.revision_log'].create({
                    'design_id': design.id,
                    'usuario_id': self.env.user.id,
                    'observaciones': f"Ítem validado por validador: {item.name}",
                    'tipo': 'validacion_validador',
                })

            # Registrar cambios en comentarios
            if 'comentario' in vals:
                self.env['design.revision_log'].create({
                    'design_id': design.id,
                    'usuario_id': self.env.user.id,
                    'observaciones': f"Comentario actualizado en ítem '{item.name}': {vals['comentario']}",
                    'tipo': 'comentario',
                })

        # Verificar si se completó el checklist después de los cambios
        if 'validado_por_disenador' in vals or 'validado_por_validador' in vals:
            for item in self:
                if item.design_id:
                    item.design_id._compute_estado_checklist()

        return res

    @api.model
    def create(self, vals):
        """Crear item con controles de permisos"""
        result = super(ChecklistItem, self).create(vals)
        
        # Registrar creación en el historial
        if result.design_id:
            self.env['design.revision_log'].create({
                'design_id': result.design_id.id,
                'usuario_id': self.env.user.id,
                'observaciones': f"Ítem de checklist creado: {result.name}",
                'tipo': 'creacion',
            })
        
        return result

    def unlink(self):
        """Eliminar items con registro en historial"""
        for record in self:
            if record.design_id:
                self.env['design.revision_log'].create({
                    'design_id': record.design_id.id,
                    'usuario_id': self.env.user.id,
                    'observaciones': f"Ítem de checklist eliminado: {record.name}",
                    'tipo': 'eliminacion',
                })
        
        return super(ChecklistItem, self).unlink()