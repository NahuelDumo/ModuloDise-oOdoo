# -*- coding: utf-8 -*-
import logging
import base64
from odoo import http, fields, _

_logger = logging.getLogger(__name__)

from odoo.http import request, route
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError

class DesignPortal(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'design_count' in counters:
            domain = self._get_designs_domain()
            values['design_count'] = request.env['design.design'].search_count(domain)
            _logger.info(f"[PORTAL] Design count calculado: {values['design_count']}")
        return values
    
    def _get_designs_domain(self):
        """Dominio base para buscar diseños visibles para el usuario actual.
        Coincide con la regla de seguridad design_design_rule_cliente."""
        _logger.info("-" * 50)
        _logger.info("[PORTAL] INICIO DE _get_designs_domain")
        
        # Obtener información del usuario y partner
        user = request.env.user
        partner = user.partner_id
        commercial_partner = partner.commercial_partner_id
        
        _logger.info(f"[PORTAL] Usuario: {user.name} (ID: {user.id})")
        _logger.info(f"[PORTAL] Partner: {partner.name} (ID: {partner.id})")
        _logger.info(f"[PORTAL] Partner Comercial: {commercial_partner.name} (ID: {commercial_partner.id})")
        _logger.info(f"[PORTAL] Grupos del usuario: {[g.name for g in user.groups_id]}")
        
        # Verificar si el partner tiene algún diseño asociado directamente
        designs_direct = request.env['design.design'].search([('cliente_id', '=', partner.id)])
        _logger.info(f"[PORTAL] Diseños asociados directamente al partner: {len(designs_direct)}")
        for idx, design in enumerate(designs_direct, 1):
            _logger.info(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}")
        
        # Verificar diseños en la jerarquía del partner comercial
        designs_hierarchy = request.env['design.design'].search([('cliente_id', 'child_of', partner.commercial_partner_id.id)])
        _logger.info(f"[PORTAL] Diseños en la jerarquía del partner comercial: {len(designs_hierarchy)}")
        for idx, design in enumerate(designs_hierarchy, 1):
            _logger.info(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}")
        
        # Dominio final con todos los filtros
        _logger.info(f"Partner comercial para el dominio del portal: {partner.commercial_partner_id.name} (ID: {partner.commercial_partner_id.id})")
        domain = [
            '|',
                ('cliente_id', '=', partner.id),
                ('cliente_id', 'child_of', partner.commercial_partner_id.id),
            ('visible_para_cliente', '=', True),
            ('state', 'in', ['cliente', 'correcciones_solicitadas', 'aprobado', 'rechazado'])

        ]
        
        _logger.info(f"[PORTAL] Dominio de búsqueda: {domain}")
        
        # Verificar cuántos diseños coinciden con el dominio completo
        matching_designs = request.env['design.design'].search(domain)
        _logger.info(f"[PORTAL] Diseños que coinciden con el dominio: {len(matching_designs)}")
        for idx, design in enumerate(matching_designs, 1):
            _logger.info(f"  {idx}. ID: {design.id}, Nombre: {design.name}, Estado: {design.state}, Cliente: {design.cliente_id.display_name}, Visible: {design.visible_para_cliente}")
        
        return domain
    
    @http.route(['/my/designs', '/my/designs/page/<int:page>'], type='http', auth="user", website=True, sitemap=False)
    def portal_my_designs(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', **kw):
        """Muestra la lista de diseños del usuario en el portal."""
        _logger.info("=" * 50)
        _logger.info("[PORTAL] INICIO DE PORTAL_MY_DESIGNS")
        _logger.info(f"[PORTAL] Usuario actual: {request.env.user.name} (ID: {request.env.user.id})")
        _logger.info(f"[PORTAL] Parámetros de URL: page={page}, date_begin={date_begin}, date_end={date_end}")
        _logger.info("=" * 50)
        
        # Obtener el dominio base
        domain = self._get_designs_domain()
        
        # Configurar la paginación
        design_count = request.env['design.design'].search_count(domain)
        pager = portal_pager(
            url="/my/designs",
            total=design_count,
            page=page,
            step=self._items_per_page
        )
        
        # Obtener los diseños paginados
        designs = request.env['design.design'].search(
            domain,
            limit=self._items_per_page,
            offset=pager['offset'],
            order='create_date desc'  # Ordenar por fecha de creación descendente
        )
        
        _logger.info(f"Dominio final usado en la búsqueda: {domain}")
        _logger.info(f"Diseños encontrados para el portal: {[d.name for d in designs]} (Total: {len(designs)})")
        
        # Preparar valores para la plantilla
        values = self._prepare_portal_layout_values()
        values.update({
            'designs': designs,
            'page_name': 'design',
            'default_url': '/my/designs',
            'pager': pager,
            'design_count': design_count,
        })
        
        _logger.info(f"Buscando diseños para el partner {request.env.user.partner_id.id} con el dominio: {domain}")
        _logger.info(f"Se encontraron {design_count} diseños.")
        
        _logger.warning(f"[PORTAL] Mostrando {len(designs)} diseños de un total de {design_count}")
        return request.render("ModuloDisenoOdoo.portal_my_designs", values)
    
    @http.route(['/my/design/<int:design_id>'], type='http', auth="user", website=True, sitemap=False)
    def portal_my_design(self, design_id, access_token=None, **kw):
        """Muestra los detalles de un diseño específico en el portal."""
        try:
                     
            if request.env.user.has_group('base.group_user'):
                design_sudo = request.env['design.design'].sudo().browse(design_id)
                if not design_sudo.exists():
                    return request.redirect('/my')
            else:
                design_sudo = self._document_check_access('design.design', design_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Generar tokens de acceso para los adjuntos si no existen
        for attachment in design_sudo.attachment_ids:
            if not attachment.access_token:
                attachment.sudo()._portal_ensure_token()
                
        # Construir datos de archivos usando base64 directamente (sin URLs externas)
        attachments = []
        for attachment in design_sudo.attachment_ids:
            # Obtener los datos del archivo en base64 (usando file_data del modelo design.image)
            file_data = attachment.file_data
            if file_data:
                # Crear data URL para descarga
                data_url = f"data:{attachment.mimetype or 'application/octet-stream'};base64,{file_data.decode('utf-8')}"
                
                # Usar image_preview para la previsualización si está disponible
                preview_url = None
                if attachment.image_preview:
                    preview_url = f"data:{attachment.mimetype or 'image/jpeg'};base64,{attachment.image_preview.decode('utf-8')}"
                
                attachments.append({
                    'id': attachment.id,
                    'name': attachment.name,
                    'mimetype': attachment.mimetype,
                    'file_size': attachment.file_size,
                    'data_url': data_url,
                    'preview_url': preview_url or data_url,  # Usar preview si existe, sino usar data_url
                    'file_extension': attachment.name.split('.')[-1].lower() if '.' in attachment.name else ''
                })

        # Obtener mensajes del chatter - incluir todos los tipos para debug
        messages = []
        for message in design_sudo.message_ids.sorted('create_date', reverse=False):
            # Mostrar todos los comentarios legibles por el portal (según reglas de seguridad)
            if (
                message.message_type == 'comment'
                and message.body
            ):
                messages.append({
                    'id': message.id,
                    'body': message.body,
                    'author_name': (message.sudo().author_id.name) or 'Sistema',
                    'date': message.create_date.strftime('%d/%m/%Y %H:%M'),
                    'message_type': message.message_type,
                    'is_internal': message.is_internal,
                })

        # Valores seguros para portal: nombres de tarea y diseñador sin acceder al modelo desde QWeb
        task_display_name = ''
        designer_display_name = ''
        try:
            task = design_sudo.sudo().task_id
            if task:
                task_display_name = task.name or ''
                designer_display_name = (task.user_ids[:1].name) or ''
        except Exception:
            # No bloquear el portal por errores de acceso a project.task
            task_display_name = ''
            designer_display_name = ''

        # Nombre seguro del cliente
        cliente_display_name = ''
        try:
            cliente_display_name = design_sudo.sudo().cliente_id.display_name or ''
        except Exception:
            cliente_display_name = ''
        
        # Agregar mensaje de prueba si no hay mensajes
        if not messages:
            messages.append({
                'id': 0,
                'body': '<p>¡Bienvenido al sistema de mensajería! Aquí aparecerán todos los mensajes entre el cliente y el equipo de diseño.</p>',
                'author_name': 'Sistema',
                'date': '15/08/2025 00:40',
                'message_type': 'notification',
                'is_internal': False,
            })

        values = self._prepare_portal_layout_values()
        values.update({
            'design': design_sudo,
            'page_name': 'design',
            'message': kw.get('message'),
            'error': kw.get('error'),  # Agregado para manejar errores
            'report_type': 'html',
            'access_token': design_sudo.access_token,
            'attachments': attachments,
            'messages': messages,
            'task_display_name': task_display_name,
            'designer_display_name': designer_display_name,
            'cliente_display_name': cliente_display_name,
        })
        return request.render("ModuloDisenoOdoo.portal_my_design", values)
    
    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        values['design_count'] = request.env['design.design'].search_count(self._get_designs_domain())
        _logger.warning(f"[PORTAL] Portal layout - design_count: {values['design_count']}")
        return values
    
    @route(['/my/design/approve'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def approve_design(self, design_id, message='', **post):
        """Aprobar diseño por parte del cliente"""
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if not self._check_design_access(design_sudo, partner):
            return request.redirect('/my')
            
        try:
            # Aprobar el diseño usando el método del modelo
            design_sudo.sudo().marcar_como_aprobado_por_cliente()
            
            # Agregar mensaje del cliente si existe
            if message and message.strip():
                design_sudo.sudo().message_post(
                    body=f"<p><strong>Comentario del cliente al aprobar:</strong></p><p>{message}</p>",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    author_id=request.env.user.partner_id.id
                )
            
            # Redirigir con mensaje de éxito
            return request.redirect(f"/my/design/{design_id}?message=design_approved")
            
        except Exception as e:
            _logger.error(f"Error al aprobar diseño: {str(e)}")
            return request.redirect(f"/my/design/{design_id}?error=approval_error")
    
    @route(['/my/design/approve-with-changes'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def approve_with_changes_design(self, design_id, message='', **post):
        """Aprobar diseño con correcciones por parte del cliente"""
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if not self._check_design_access(design_sudo, partner):
            return request.redirect('/my')
            
        # Verificar límite de modificaciones (máximo 3)
        if design_sudo.contador_modificaciones >= 3:
            return request.redirect(f"/my/design/{design_id}?error=max_modifications_reached")
            
        try:
            # Solicitar correcciones usando el método del modelo
            design_sudo.sudo().action_solicitar_correcciones(message or "Cliente solicita correcciones")
            
            # Redirigir con mensaje de éxito
            return request.redirect(f"/my/design/{design_id}?message=design_corrections_requested")
            
        except Exception as e:
            _logger.error(f"Error al solicitar correcciones: {str(e)}")
            return request.redirect(f"/my/design/{design_id}?error=error_processing_changes")
    
    @route(['/my/design/reject'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def reject_design(self, design_id, message='', **post):
        """Rechazar diseño por parte del cliente"""
        try:
            design_sudo = self._document_check_access('design.design', int(design_id))
        except (AccessError, MissingError):
            return request.redirect('/my')
            
        # Verificar que el usuario tenga acceso a este diseño
        partner = request.env.user.partner_id
        if not self._check_design_access(design_sudo, partner):
            return request.redirect('/my')
            
        try:
            design_sudo.sudo().marcar_como_rechazado(message or "Cliente rechaza el diseño")
            
            # Redirigir con mensaje de éxito
            return request.redirect(f"/my/design/{design_id}?message=design_rejected")
            
        except Exception as e:
            _logger.error(f"Error al rechazar diseño: {str(e)}")
            return request.redirect(f"/my/design/{design_id}?error=rejection_error")
    
    def _check_design_access(self, design, partner):
        """Verificar que el partner tiene acceso al diseño"""
        return (design.cliente_id.id == partner.id or 
                design.cliente_id.id in partner.commercial_partner_id.child_ids.ids or
                design.cliente_id.id == partner.commercial_partner_id.id)
    
    def _document_check_access(self, model_name, document_id, access_token=None):
        """Verificar acceso a un documento de manera segura para usuarios del portal"""
        try:
            # Si no es nuestro modelo personalizado, delegar al comportamiento estándar del portal
            if model_name != 'design.design':
                return super()._document_check_access(model_name, document_id, access_token=access_token)

            # Obtener el registro con el usuario actual
            document = request.env[model_name].browse(document_id)
            
            # Verificar que el documento existe
            if not document.exists():
                _logger.warning(f"Documento {model_name} ID {document_id} no encontrado")
                raise MissingError(_("El documento no existe o fue eliminado"))
                
            # Verificar que el usuario sea el cliente asignado al diseño usando el método auxiliar
            partner = request.env.user.partner_id
            if not self._check_design_access(document, partner):
                _logger.warning(
                    f"Acceso denegado: Usuario {request.env.user.id} intentó acceder "
                    f"al diseño {document_id} que pertenece al cliente {document.cliente_id.id}"
                )
                raise AccessError(_("No tiene permiso para acceder a este diseño"))
                
            # Verificar permisos básicos de lectura
            try:
                document.check_access_rights('read')
                document.check_access_rule('read')
            except AccessError as e:
                _logger.warning(f"Error de permisos en documento {document_id}: {str(e)}")
                raise AccessError(_("No tiene permiso para ver este documento"))
                
            return document
            
        except Exception as e:
            _logger.error(f"Error en _document_check_access: {str(e)}", exc_info=True)
            raise
    
    @route(['/my/design/<int:design_id>/message'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_design_message(self, design_id, access_token=None, **kw):
        """Enviar mensaje desde el portal"""
        try:
            # Para usuarios internos, usar sudo directamente
            if request.env.user.has_group('base.group_user'):
                design_sudo = request.env['design.design'].sudo().browse(design_id)
                if not design_sudo.exists():
                    return request.redirect('/my')
            else:
                design_sudo = self._document_check_access('design.design', design_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        message_body = kw.get('message_body', '').strip()
        if message_body:
            # Usar mail.mt_comment para que sea visible en el portal
            design_sudo.sudo().message_post(
                body=message_body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                author_id=request.env.user.partner_id.id
            )
        
        return request.redirect(f'/my/design/{design_id}?access_token={access_token or design_sudo.access_token}')

    @route(['/my/design/<int:design_id>/comment'], type='http', auth="user", methods=['POST'], website=True, csrf=True)
    def portal_design_comment(self, design_id, access_token=None, **kw):
        """Agregar comentario desde el portal"""
        try:
            # Para usuarios internos, usar sudo directamente
            if request.env.user.has_group('base.group_user'):
                design_sudo = request.env['design.design'].sudo().browse(design_id)
                if not design_sudo.exists():
                    return request.redirect('/my')
            else:
                design_sudo = self._document_check_access('design.design', design_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        mensaje_cliente = kw.get('mensaje_cliente', '').strip()
        if mensaje_cliente:
            # Actualizar el campo ultimo_mensaje_cliente
            design_sudo.sudo().write({
                'ultimo_mensaje_cliente': mensaje_cliente
            })
            
            # Usar mail.mt_comment para que sea visible en el portal
            design_sudo.sudo().message_post(
                body=f"<p><strong>Comentario del cliente:</strong></p><p>{mensaje_cliente}</p>",
                message_type='comment',
                subtype_xmlid='mail.mt_comment'
            )
        
        return request.redirect(f'/my/design/{design_id}?access_token={access_token or design_sudo.access_token}')