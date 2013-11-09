# -*- coding: utf-8 -*-
#
# necronomicon.py
# This file is part of Necronomicon, a plugin for gedit
#
# Copyright (C) 2013 Jeffery To <jeffery.to@gmail.com>
# https://github.com/jefferyto/gedit-necronomicon
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import GObject, Gtk, Gio, Gedit

# we fake window-added / window-removed signals
# since Gedit.App wasn't a Gtk.Application until gedit 3.8

class NecronomiconPluginWindowActivatable(GObject.Object, Gedit.WindowActivatable):
	__gtype_name__ = 'NecronomiconPluginWindowActivatable'

	window = GObject.property(type=Gedit.Window)

	def __init__(self):
		GObject.Object.__init__(self)
		self._helper = getattr(Gedit.App.get_default(), NecronomiconPluginAppActivatable.APP_HELPER)

	def do_activate(self):
		self._helper.window_added(self.window)

	def do_deactivate(self):
		self._helper.window_removed(self.window)

	def do_update_state(self):
		pass

class NecronomiconPluginAppHelper(GObject.Object):
	__gtype_name__ = 'NecronomiconPluginAppHelper'

	__gsignals__ = {
		'window-added': (GObject.SIGNAL_RUN_FIRST, None, (Gtk.Window,)),
		'window-removed': (GObject.SIGNAL_RUN_FIRST, None, (Gtk.Window,))
	}

	def __init__(self):
		GObject.Object.__init__(self)

	def window_added(self, window):
		self.emit('window-added', window)

	def window_removed(self, window):
		self.emit('window-removed', window)

class NecronomiconPluginAppActivatable(GObject.Object, Gedit.AppActivatable):
	__gtype_name__ = 'NecronomiconPluginAppActivatable'

	app = GObject.property(type=Gedit.App)

	REOPEN_ACCELERATOR = '<shift><control>O'

	MAX_RECENTS_SETTINGS_SCHEMA = 'org.gnome.gedit.preferences.ui'

	REOPEN_MENU_PATH = '/MenuBar/FileMenu/FileOps_2/NecronomiconPluginReopenMenu/NecronomiconPluginReopenPlaceholder'

	APP_HELPER = 'NecronomiconPluginAppHelper'

	HANDLER_IDS = 'NecronomiconPluginHandlerIds'

	TAB_SUMMARY = 'NecronomiconPluginTabSummary'

	def __init__(self):
		GObject.Object.__init__(self)

	def do_activate(self):
		app = self.app

		helper = NecronomiconPluginAppHelper()
		setattr(app, self.APP_HELPER, helper)

		settings = Gio.Settings.new(self.MAX_RECENTS_SETTINGS_SCHEMA)
		max_recents = settings.get_uint('max-recents')

		self._connect_handlers(helper, ('window-added', 'window-removed'), 'app')

		self._closed_files = []
		self._max_closed_files = max_recents * 10
		self._max_reopen_items = max_recents
		self._windows = {}

		for window in app.get_windows():
			self.on_app_window_added(app, window)

	def do_deactivate(self):
		app = self.app

		for window in app.get_windows():
			self.on_app_window_removed(app, window)

		self._disconnect_handlers(getattr(app, self.APP_HELPER))
		delattr(app, self.APP_HELPER)

		self._closed_files = None
		self._max_closed_files = None
		self._max_reopen_items = None
		self._windows = None

	def on_app_window_added(self, app, window):
		if not window in self._windows:
			ui_manager = window.get_ui_manager()

			menu_action_group = Gtk.ActionGroup('NecronomiconPluginActions')
			menu_action_group.set_translation_domain('gedit')
			ui_manager.insert_action_group(menu_action_group, -1)

			menu_action = Gtk.Action('NecronomiconPluginReopen', _("Recently Closed"), _("Recently closed files"), None)
			menu_action.set_property('hide-if-empty', False)
			menu_action.set_sensitive(False)
			menu_action_group.add_action(menu_action)

			menu_ui_str = """
				<ui>
					<menubar name="MenuBar">
						<menu name="FileMenu" action="File">
							<placeholder name="FileOps_2">
								<separator/>
								<menu name="NecronomiconPluginReopenMenu" action="NecronomiconPluginReopen">
									<placeholder name="NecronomiconPluginReopenPlaceholder"/>
								</menu>
							</placeholder>
						</menu>
					</menubar>
				</ui>"""
			menu_ui_id = ui_manager.add_ui_from_string(menu_ui_str)

			self._connect_handlers(window, ('tab-added', 'tab-removed'), 'window')

			self._windows[window] = {
				'menu_action_group': menu_action_group,
				'menu_ui_id': menu_ui_id,
				'menu_action': menu_action,
				'reopen_action_group': Gtk.ActionGroup('NecronomiconPluginReopenActions'),
				'reopen_ui_id': 0,
				'update_menu_id': 0
			}

			for doc in window.get_documents():
				self.on_window_tab_added(window, Gedit.Tab.get_from_document(doc))

			self._update_window_menu(window, self._windows[window])

	def on_app_window_removed(self, app, window):
		if window in self._windows:
			data = self._windows[window]

			for doc in window.get_documents():
				self.on_window_tab_removed(window, Gedit.Tab.get_from_document(doc))

			self._disconnect_handlers(window)

			update_menu_id = data['update_menu_id']
			if update_menu_id:
				GObject.source_remove(update_menu_id)
				data['update_menu_id'] = 0

			self._clear_window_menu(window, data)

			ui_manager = window.get_ui_manager()
			ui_manager.remove_ui(data['menu_ui_id'])
			ui_manager.remove_action_group(data['menu_action_group'])
			ui_manager.ensure_update()

			del self._windows[window]

	def on_window_tab_added(self, window, tab):
		self._file_opened(tab)

		doc = tab.get_document()
		setattr(doc, self.TAB_SUMMARY, self._get_tab_summary(tab))
		self._connect_handlers(doc, ('loaded', 'saved'), self.on_document_loaded_saved)

	def on_window_tab_removed(self, window, tab):
		doc = tab.get_document()
		self._disconnect_handlers(doc)
		delattr(doc, self.TAB_SUMMARY)

		self._file_closed(tab)

	def on_document_loaded_saved(self, doc, error):
		tab = Gedit.Tab.get_from_document(doc)
		prev_summary = getattr(doc, self.TAB_SUMMARY)
		cur_summary = self._get_tab_summary(tab)

		if not prev_summary or not cur_summary['location'].equal(prev_summary['location']):
			if prev_summary:
				summary = cur_summary.copy()
				summary['location'] = prev_summary['location']
				self._file_closed(summary)

			self._file_opened(cur_summary)

			setattr(doc, self.TAB_SUMMARY, cur_summary)

	def _file_opened(self, tab_or_summary):
		closed_files = self._closed_files
		num_closed_files = len(closed_files)

		if isinstance(tab_or_summary, Gedit.Tab):
			location = self._get_tab_location(tab_or_summary)
		elif tab_or_summary:
			location = tab_or_summary['location']
		else:
			location = None

		if location:
			closed_files[:] = [f for f in closed_files if not f['location'].equal(location)]

		if len(closed_files) != num_closed_files:
			self._update_menus()

	def _file_closed(self, tab_or_summary):
		closed_files = self._closed_files
		summary = self._get_tab_summary(tab_or_summary) if isinstance(tab_or_summary, Gedit.Tab) else tab_or_summary

		if summary:
			location = summary['location']
			closed_files[:] = [f for f in closed_files if not f['location'].equal(location)]

			closed_files.insert(0, summary)

			del closed_files[self._max_closed_files:]

			self._update_menus()

	def _get_tab_location(self, tab):
		return tab.get_document().get_location()

	def _get_tab_summary(self, tab):
		location = self._get_tab_location(tab)
		summary = None

		if location:
			view = tab.get_view()
			doc = tab.get_document()
			text_iter = doc.get_iter_at_mark(doc.get_insert())

			summary = {
				'location': location,
				'mime_type': doc.get_mime_type(),
				'encoding': doc.get_property('encoding'),
				'line_pos': text_iter.get_line(),
				'column_pos': view.get_visual_column(text_iter)
			}

		return summary

	def _update_menus(self):
		for window, data in self._windows.items():
			self._update_window_menu(window, data)

	def _update_window_menu(self, window, data):
		if not data['update_menu_id']:
			data['update_menu_id'] = GObject.idle_add(self._update_window_menu_idle, window, data)

	def _update_window_menu_idle(self, window, data):
		self._clear_window_menu(window, data)

		closed_files = self._closed_files
		ui_manager = window.get_ui_manager()

		if closed_files:
			reopen_ui_id = ui_manager.new_merge_id()
			action_group = data['reopen_action_group']
			max_items = self._max_reopen_items
			num = 0

			for f in closed_files:
				if num >= max_items:
					break

				location = f['location']
				content_type = Gio.content_type_from_mime_type(f['mime_type'])

				name = 'NecronomiconPluginReopenFile_%d' % num
				label = Gedit.utils_escape_underscores(location.get_basename(), -1)
				# Translators: %s is a URI
				tooltip = _("Reopen '%s'") % Gedit.utils_replace_home_dir_with_tilde(location.get_parse_name())

				action = Gtk.Action(name, label, tooltip, None)
				action.set_always_show_image(True)
				if content_type:
					action.set_gicon(Gio.content_type_get_icon(content_type))
				self._connect_handlers(action, ('activate',), 'reopen_action', window, f)

				if num == 0:
					action_group.add_action_with_accel(action, self.REOPEN_ACCELERATOR)
				else:
					action_group.add_action(action)

				ui_manager.add_ui(reopen_ui_id, self.REOPEN_MENU_PATH, name, name, Gtk.UIManagerItemType.MENUITEM, False)

				num += 1

			ui_manager.insert_action_group(action_group, -1)
			data['menu_action'].set_sensitive(True)
			data['reopen_ui_id'] = reopen_ui_id

		ui_manager.ensure_update()

		data['update_menu_id'] = 0
		return False

	def _clear_window_menu(self, window, data):
		data['menu_action'].set_sensitive(False)

		reopen_ui_id = data['reopen_ui_id']
		action_group = data['reopen_action_group']

		if reopen_ui_id:
			ui_manager = window.get_ui_manager()
			ui_manager.remove_ui(reopen_ui_id)
			ui_manager.remove_action_group(action_group)
			data['reopen_ui_id'] = 0

		for action in action_group.list_actions():
			self._disconnect_handlers(action)
			action_group.remove_action(action)

	def on_reopen_action_activate(self, action, window, summary):
		# line and column pos start from 1, for some reason
		Gedit.commands_load_location(
			window, summary['location'], summary['encoding'],
			summary['line_pos'] + 1, summary['column_pos'] + 1)

	def _connect_handlers(self, obj, signals, m, *args):
		HANDLER_IDS = self.HANDLER_IDS
		l_ids = getattr(obj, HANDLER_IDS) if hasattr(obj, HANDLER_IDS) else []

		for signal in signals:
			if type(m).__name__ == 'str':
				method = getattr(self, 'on_' + m + '_' + signal.replace('-', '_').replace('::', '_'))
			else:
				method = m
			l_ids.append(obj.connect(signal, method, *args))

		setattr(obj, HANDLER_IDS, l_ids)

	def _disconnect_handlers(self, obj):
		HANDLER_IDS = self.HANDLER_IDS
		if hasattr(obj, HANDLER_IDS):
			for l_id in getattr(obj, HANDLER_IDS):
				obj.disconnect(l_id)

			delattr(obj, HANDLER_IDS)
