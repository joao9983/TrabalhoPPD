"""
Interface Gráfica com Tkinter
Proporciona interface completa para comunicação baseada em localização.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
from src.network.sync_client import SyncClient
from src.messaging.async_producer import AsyncProducer
from src.utils.utils import format_distance, validate_coordinates, is_valid_radius

class ChatGUI:
    def __init__(self, root, initialize_callback):
        self.root = root
        self.initialize_callback = initialize_callback
        self.user_state = None
        self.contacts_manager = None
        self.sync_server = None
        self.async_consumer = None
        self.sync_client = None
        self.async_producer = None
        
        self.root.title("Sistema de Comunicação por Localização")
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
        # Variáveis de controle
        self.selected_contact = tk.StringVar()
        self.current_chat_user = None
        
        # Controle de usuários descobertos para evitar spam
        self.discovered_users = set()
        
        self._setup_login()
    
    def _safe_after(self, delay, callback, *args):
        """Método auxiliar para chamadas thread-safe ao root.after"""
        if hasattr(self, 'root') and self.root:
            self.root.after(delay, callback, *args)
        else:
            # Se ainda não tem root, executa diretamente (pode ser arriscado, mas é fallback)
            if delay == 0:
                try:
                    callback(*args)
                except:
                    pass
    
    def _setup_login(self):
        """Configura tela de login inicial"""
        # Frame principal de login
        login_frame = tk.Frame(self.root)
        login_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Título
        title_label = tk.Label(login_frame, text="Sistema de Comunicação por Localização", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Frame para campos de entrada
        fields_frame = tk.Frame(login_frame)
        fields_frame.pack(pady=10)
        
        # Nome de usuário
        tk.Label(fields_frame, text="Nome de usuário:", font=("Arial", 10)).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.username_entry = tk.Entry(fields_frame, font=("Arial", 10), width=20)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Latitude
        tk.Label(fields_frame, text="Latitude:", font=("Arial", 10)).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.lat_entry = tk.Entry(fields_frame, font=("Arial", 10), width=20)
        self.lat_entry.grid(row=1, column=1, padx=5, pady=5)
        self.lat_entry.insert(0, "-23.5505")  # São Paulo como padrão
        
        # Longitude
        tk.Label(fields_frame, text="Longitude:", font=("Arial", 10)).grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.lon_entry = tk.Entry(fields_frame, font=("Arial", 10), width=20)
        self.lon_entry.grid(row=2, column=1, padx=5, pady=5)
        self.lon_entry.insert(0, "-46.6333")  # São Paulo como padrão
        
        # Raio
        tk.Label(fields_frame, text="Raio (metros):", font=("Arial", 10)).grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.radius_entry = tk.Entry(fields_frame, font=("Arial", 10), width=20)
        self.radius_entry.grid(row=3, column=1, padx=5, pady=5)
        self.radius_entry.insert(0, "1000")
        
        # Botão de login
        login_btn = tk.Button(fields_frame, text="Entrar", command=self._handle_login,
                             font=("Arial", 10), bg="#4CAF50", fg="white", width=15)
        login_btn.grid(row=4, column=0, columnspan=2, pady=20)
        
        # Bind Enter key
        self.root.bind('<Return>', lambda e: self._handle_login())
        
        # Foco no campo de usuário
        self.username_entry.focus()
    
    def _handle_login(self):
        """Processa login e inicializa sistema"""
        username = self.username_entry.get().strip()
        lat_str = self.lat_entry.get().strip()
        lon_str = self.lon_entry.get().strip()
        radius_str = self.radius_entry.get().strip()
        
        # Validações
        if not username:
            messagebox.showerror("Erro", "Nome de usuário obrigatório")
            return
        
        try:
            latitude = float(lat_str)
            longitude = float(lon_str)
            radius = float(radius_str)
        except ValueError:
            messagebox.showerror("Erro", "Coordenadas e raio devem ser números válidos")
            return
        
        if not validate_coordinates(latitude, longitude):
            messagebox.showerror("Erro", "Coordenadas inválidas")
            return
        
        if not is_valid_radius(radius):
            messagebox.showerror("Erro", "Raio deve estar entre 100m e 50km")
            return
        
        # Limpa tela de login
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Inicializa componentes
        if self.initialize_callback(username, latitude, longitude, radius):
            self._setup_main_interface()
        else:
            messagebox.showerror("Erro", "Falha ao inicializar sistema")
            self.root.quit()
    
    def set_components(self, user_state, contacts_manager, sync_server, async_consumer):
        """Define componentes do sistema após inicialização"""
        self.user_state = user_state
        self.contacts_manager = contacts_manager
        self.sync_server = sync_server
        self.async_consumer = async_consumer
        
        # Inicializa clientes
        self.sync_client = SyncClient(user_state, self, contacts_manager)
        self.async_producer = AsyncProducer(user_state)
        
        # Inicia descoberta de contatos
        self.contacts_manager.start_discovery()
        
        # Se iniciou como online, automaticamente processa mensagens offline (MOM pattern)
        if user_state.status == "online":
            # Delay para garantir que async_consumer está pronto
            self.root.after(2000, self._auto_process_offline_messages)
            # Inicia verificação automática contínua para usuário que começou online
            self.root.after(3000, lambda: self.async_consumer.start_auto_check_when_online() if self.async_consumer else None)
    
    def _setup_main_interface(self):
        """Configura interface principal"""
        # Menu superior
        self._create_menu()
        
        # Frame principal
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configurar grid
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)
        
        # Painel de informações do usuário
        self._create_user_info_panel(main_frame)
        
        # Painel de contatos
        self._create_contacts_panel(main_frame)
        
        # Painel de chat
        self._create_chat_panel(main_frame)
        
        # Painel de controles
        self._create_controls_panel(main_frame)
        
        # Barra de status
        self._create_status_bar()
        
        # Inicia timer para atualizar interface
        self._start_update_timer()
    
    def _create_menu(self):
        """Cria menu superior"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu Arquivo
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Arquivo", menu=file_menu)
        file_menu.add_command(label="Alterar Localização", command=self._change_location)
        file_menu.add_command(label="Alterar Raio", command=self._change_radius)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self._quit_application)
        
        # Menu Status
        status_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Status", menu=status_menu)
        status_menu.add_command(label="Online", command=lambda: self._change_status("online"))
        status_menu.add_command(label="Ausente", command=lambda: self._change_status("away"))
        status_menu.add_command(label="Ocupado", command=lambda: self._change_status("busy"))
        status_menu.add_command(label="Offline", command=lambda: self._change_status("offline"))
        
        # Menu Contatos
        contacts_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Contatos", menu=contacts_menu)
        contacts_menu.add_command(label="Adicionar Contato Manual", command=self._add_manual_contact)
        contacts_menu.add_command(label="Remover Contato", command=self._remove_contact)
        contacts_menu.add_separator()
        contacts_menu.add_command(label="Atualizar Lista", command=self._refresh_contacts)
    
    def _create_user_info_panel(self, parent):
        """Cria painel com informações do usuário"""
        info_frame = tk.LabelFrame(parent, text="Informações do Usuário", font=("Arial", 10, "bold"))
        info_frame.grid(row=0, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        
        self.user_info_label = tk.Label(info_frame, text="", font=("Arial", 9))
        self.user_info_label.pack(pady=5)
        
        self._update_user_info()
    
    def _create_contacts_panel(self, parent):
        """Cria painel de contatos"""
        contacts_frame = tk.LabelFrame(parent, text="Contatos no Raio", font=("Arial", 10, "bold"))
        contacts_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)
        contacts_frame.grid_rowconfigure(0, weight=1)
        
        # Lista de contatos
        self.contacts_listbox = tk.Listbox(contacts_frame, font=("Arial", 9))
        self.contacts_listbox.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        contacts_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollbar para lista
        contacts_scrollbar = tk.Scrollbar(contacts_frame, orient="vertical")
        contacts_scrollbar.grid(row=0, column=1, sticky='ns', pady=5)
        self.contacts_listbox.config(yscrollcommand=contacts_scrollbar.set)
        contacts_scrollbar.config(command=self.contacts_listbox.yview)
        
        # Bind duplo clique
        self.contacts_listbox.bind('<Double-1>', self._on_contact_double_click)
        
        # Botões de ação
        btn_frame = tk.Frame(contacts_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5)
        
        tk.Button(btn_frame, text="Chat Síncrono", command=self._start_sync_chat,
                 font=("Arial", 8)).pack(side='left', padx=2)
        tk.Button(btn_frame, text="Mensagem Offline", command=self._send_async_message,
                 font=("Arial", 8)).pack(side='left', padx=2)
    
    def _create_chat_panel(self, parent):
        """Cria painel de chat"""
        chat_frame = tk.LabelFrame(parent, text="Chat", font=("Arial", 10, "bold"))
        chat_frame.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
        chat_frame.grid_rowconfigure(0, weight=1)
        chat_frame.grid_columnconfigure(0, weight=1)
        
        # Área de mensagens
        self.chat_text = tk.Text(chat_frame, state='disabled', wrap='word', font=("Arial", 9))
        self.chat_text.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        # Scrollbar para chat
        chat_scrollbar = tk.Scrollbar(chat_frame, orient="vertical")
        chat_scrollbar.grid(row=0, column=1, sticky='ns', pady=5)
        self.chat_text.config(yscrollcommand=chat_scrollbar.set)
        chat_scrollbar.config(command=self.chat_text.yview)
        
        # Campo de entrada de mensagem
        msg_frame = tk.Frame(chat_frame)
        msg_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        msg_frame.grid_columnconfigure(0, weight=1)
        
        self.message_entry = tk.Entry(msg_frame, font=("Arial", 9))
        self.message_entry.grid(row=0, column=0, sticky='ew', padx=(0, 5))
        
        send_btn = tk.Button(msg_frame, text="Enviar", command=self._send_message,
                           font=("Arial", 8))
        send_btn.grid(row=0, column=1)
        
        # Bind Enter key
        self.message_entry.bind('<Return>', lambda e: self._send_message())
    
    def _create_controls_panel(self, parent):
        """Cria painel de controles"""
        controls_frame = tk.LabelFrame(parent, text="Controles", font=("Arial", 10, "bold"))
        controls_frame.grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        
        # Botões de controle
        btn_container = tk.Frame(controls_frame)
        btn_container.pack(pady=5)
        
        tk.Button(btn_container, text="Limpar Chat", command=self._clear_chat,
                 font=("Arial", 8)).pack(side='left', padx=5)
        tk.Button(btn_container, text="Desconectar Chat", command=self._disconnect_current_chat,
                 font=("Arial", 8)).pack(side='left', padx=5)
        tk.Button(btn_container, text="Verificar Msgs Offline", command=self._check_offline_messages,
                 font=("Arial", 8)).pack(side='left', padx=5)
    
    def _create_status_bar(self):
        """Cria barra de status"""
        self.status_bar = tk.Label(self.root, text="Pronto", bd=1, relief='sunken', anchor='w')
        self.status_bar.pack(side='bottom', fill='x')
    
    def _start_update_timer(self):
        """Inicia timer para atualizar interface"""
        self._update_interface()
        self.root.after(5000, self._start_update_timer)  # Atualiza a cada 5 segundos
    
    def _update_interface(self):
        """Atualiza interface periodicamente"""
        self._update_user_info()
        self._refresh_contacts()
    
    def _update_user_info(self):
        """Atualiza informações do usuário"""
        if not self.user_state:
            return
        
        info = self.user_state.get_info()
        text = (f"Usuário: {info['username']} | "
                f"Status: {info['status']} | "
                f"Localização: {info['latitude']:.4f}, {info['longitude']:.4f} | "
                f"Raio: {format_distance(info['radius'])}")
        
        self.user_info_label.config(text=text)
    
    def _refresh_contacts(self):
        """Atualiza lista de contatos"""
        if not self.contacts_manager:
            return
        
        contacts = self.contacts_manager.get_contacts_in_range()
        
        # Limpa lista atual
        self.contacts_listbox.delete(0, tk.END)
        
        # Adiciona contatos
        for username, contact in contacts.items():
            distance = format_distance(contact.get('distance', 0))
            status = contact.get('status', 'unknown')
            
            display_text = f"{username} ({status}) - {distance}"
            self.contacts_listbox.insert(tk.END, display_text)
        
        # Atualiza status bar
        count = len(contacts)
        self.status_bar.config(text=f"{count} contato(s) no raio")
    
    def _on_contact_double_click(self, event):
        """Manipula duplo clique em contato"""
        selection = self.contacts_listbox.curselection()
        if selection:
            contact_text = self.contacts_listbox.get(selection[0])
            username = contact_text.split(' ')[0]
            self._start_sync_chat_with_user(username)
    
    def _start_sync_chat(self):
        """Inicia chat síncrono com contato selecionado"""
        selection = self.contacts_listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um contato")
            return
        
        contact_text = self.contacts_listbox.get(selection[0])
        username = contact_text.split(' ')[0]
        self._start_sync_chat_with_user(username)
    
    def _start_sync_chat_with_user(self, username):
        """Inicia chat síncrono com usuário específico"""
        if not self.sync_client:
            messagebox.showerror("Erro", "Cliente síncrono não disponível")
            return
        
        # Verifica se já está conectado
        if self.sync_client.is_connected_to_user(username):
            self.current_chat_user = username
            self._add_chat_message(f"[SISTEMA] Já conectado a {username}")
            return
        
        # Tenta conectar
        success, message = self.sync_client.connect_to_user(username)
        
        if success:
            self.current_chat_user = username
            self._add_chat_message(f"[SISTEMA] Conectado a {username} para chat síncrono")
        else:
            messagebox.showerror("Erro", f"Falha ao conectar: {message}")
    
    def _send_async_message(self):
        """Envia mensagem assíncrona para contato selecionado"""
        selection = self.contacts_listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um contato")
            return
        
        contact_text = self.contacts_listbox.get(selection[0])
        username = contact_text.split(' ')[0]
        
        message = simpledialog.askstring("Mensagem Offline", 
                                       f"Mensagem para {username}:")
        
        if message:
            if self.async_producer:
                success, result = self.async_producer.send_async_message(username, message)
                if success:
                    self._add_chat_message(f"[OFFLINE ENVIADA] Para {username}: {message}")
                else:
                    messagebox.showerror("Erro", f"Falha ao enviar: {result}")
            else:
                messagebox.showerror("Erro", "Produtor assíncrono não disponível")
    
    def _send_message(self):
        """Envia mensagem no chat atual"""
        message = self.message_entry.get().strip()
        if not message:
            return
        
        self.message_entry.delete(0, tk.END)
        
        if self.current_chat_user:
            # Chat síncrono
            if self.sync_client and self.sync_client.is_connected_to_user(self.current_chat_user):
                success, result = self.sync_client.send_message(self.current_chat_user, message)
                if not success:
                    self._add_chat_message(f"[ERRO] {result}")
            else:
                self._add_chat_message("[ERRO] Não conectado para chat síncrono")
        else:
            self._add_chat_message("[ERRO] Nenhum chat ativo")
    
    def _add_chat_message(self, message):
        """Adiciona mensagem ao chat"""
        self.chat_text.config(state='normal')
        self.chat_text.insert(tk.END, message + '\n')
        self.chat_text.config(state='disabled')
        self.chat_text.see(tk.END)
    
    def _clear_chat(self):
        """Limpa área de chat"""
        self.chat_text.config(state='normal')
        self.chat_text.delete(1.0, tk.END)
        self.chat_text.config(state='disabled')
    
    def _disconnect_current_chat(self):
        """Desconecta chat atual"""
        if self.current_chat_user and self.sync_client:
            success, message = self.sync_client.disconnect_from_user(self.current_chat_user)
            self._add_chat_message(f"[SISTEMA] {message}")
            self.current_chat_user = None
    
    def _check_offline_messages(self):
        """Verifica mensagens offline manualmente - só funciona quando NÃO está online"""
        if not self.user_state:
            messagebox.showerror("Erro", "Estado do usuário não disponível")
            return
        
        # Só permite verificar mensagens offline quando não está online
        if self.user_state.status == "online":
            messagebox.showwarning("Aviso", "Verificação manual só disponível quando não estiver online.\nQuando online, mensagens são processadas automaticamente.")
            return
        
        if self.async_consumer:
            count = self.async_consumer.consume_pending_messages()
            if count > 0:
                self._add_chat_message(f"[MANUAL] {count} mensagem(s) offline processada(s)")
            else:
                self._add_chat_message("[SISTEMA] Nenhuma mensagem offline pendente")
        else:
            messagebox.showerror("Erro", "Consumidor não disponível")
    
    def _change_location(self):
        """Altera localização do usuário"""
        if not self.user_state:
            return
        
        current = self.user_state.get_info()
        
        lat = simpledialog.askfloat("Nova Latitude", 
                                   f"Latitude atual: {current['latitude']}")
        if lat is None:
            return
        
        lon = simpledialog.askfloat("Nova Longitude", 
                                   f"Longitude atual: {current['longitude']}")
        if lon is None:
            return
        
        if validate_coordinates(lat, lon):
            self.user_state.update_location(lat, lon)
            self._add_chat_message(f"[SISTEMA] Localização atualizada: {lat}, {lon}")
        else:
            messagebox.showerror("Erro", "Coordenadas inválidas")
    
    def _change_radius(self):
        """Altera raio de comunicação"""
        if not self.user_state:
            return
        
        current = self.user_state.get_info()
        
        radius = simpledialog.askfloat("Novo Raio", 
                                     f"Raio atual: {current['radius']}m")
        if radius is None:
            return
        
        if is_valid_radius(radius):
            if self.contacts_manager:
                self.contacts_manager.update_user_radius(radius)
            else:
                self.user_state.update_radius(radius)
            self._add_chat_message(f"[SISTEMA] Raio atualizado: {format_distance(radius)}")
        else:
            messagebox.showerror("Erro", "Raio deve estar entre 100m e 50km")
    
    def _change_status(self, new_status):
        """Altera status do usuário"""
        if not self.user_state:
            return
        
        old_status = self.user_state.status
        
        if self.user_state.set_status(new_status):
            self._add_chat_message(f"[SISTEMA] Status alterado para: {new_status}")
            
            # Se mudou para online, automaticamente processa mensagens offline via MOM
            if new_status == "online" and old_status != "online":
                self._auto_process_offline_messages()
                # Inicia verificação automática contínua para usuário online
                if self.async_consumer:
                    self.async_consumer.start_auto_check_when_online()
            
            # Se mudou para qualquer status diferente de online, para verificação automática
            if new_status != "online" and old_status == "online":
                if self.async_consumer:
                    self.async_consumer.stop_auto_check_when_offline()
            
            # Envia broadcast de mudança de status
            if self.async_producer:
                self.async_producer.send_status_update(new_status)
        else:
            messagebox.showerror("Erro", "Status inválido")
    
    def _auto_process_offline_messages(self):
        """Automaticamente processa mensagens offline quando muda para status 'online' (MOM pattern)"""
        if self.async_consumer:
            count = self.async_consumer.consume_pending_messages()
            if count > 0:
                self._add_chat_message(f"[MOM] {count} mensagem(s) offline recebida(s) automaticamente")
    
    def _add_manual_contact(self):
        """Adiciona contato manualmente"""
        username = simpledialog.askstring("Novo Contato", "Nome do usuário:")
        if not username:
            return
        
        lat = simpledialog.askfloat("Latitude", "Latitude do contato:")
        if lat is None:
            return
        
        lon = simpledialog.askfloat("Longitude", "Longitude do contato:")
        if lon is None:
            return
        
        if validate_coordinates(lat, lon):
            if self.contacts_manager:
                success = self.contacts_manager.add_manual_contact(username, lat, lon)
                if success:
                    self._add_chat_message(f"[SISTEMA] Contato {username} adicionado")
                else:
                    messagebox.showerror("Erro", "Falha ao adicionar contato")
            else:
                messagebox.showerror("Erro", "Gerenciador de contatos não disponível")
        else:
            messagebox.showerror("Erro", "Coordenadas inválidas")
    
    def _remove_contact(self):
        """Remove contato selecionado"""
        selection = self.contacts_listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um contato")
            return
        
        contact_text = self.contacts_listbox.get(selection[0])
        username = contact_text.split(' ')[0]
        
        if messagebox.askyesno("Confirmar", f"Remover contato {username}?"):
            if self.contacts_manager:
                success = self.contacts_manager.remove_contact(username)
                if success:
                    self._add_chat_message(f"[SISTEMA] Contato {username} removido")
                else:
                    messagebox.showerror("Erro", "Falha ao remover contato")
    
    def _quit_application(self):
        """Encerra aplicação"""
        if messagebox.askyesno("Sair", "Deseja realmente sair?"):
            self.root.quit()
    
    # Métodos para callbacks dos componentes
    def display_sync_message(self, message):
        """Exibe mensagem síncrona (thread-safe)"""
        self._safe_after(0, self._add_chat_message, message)
    
    def display_async_message(self, message):
        """Exibe mensagem assíncrona (thread-safe)"""
        self._safe_after(0, self._add_chat_message, message)
    
    def on_sync_connection(self, username, connected):
        """Callback para conexão síncrona"""
        if connected:
            status = "reconectou"
            # Remove da lista de descobertos para que seja anunciado novamente
            if username in self.discovered_users:
                self.discovered_users.remove(username)
        else:
            status = "desconectou"
            # Mantém na lista para não anunciar novamente se reconectar rapidamente
        
        self._safe_after(0, self._add_chat_message, f"[SISTEMA] {username} {status}")
    
    def on_location_update(self, username, lat, lon, status):
        """Callback para atualização de localização"""
        message = f"[SISTEMA] {username} atualizou localização: {lat:.4f}, {lon:.4f}"
        self._safe_after(0, self._add_chat_message, message)
    
    def on_status_update(self, username, new_status):
        """Callback para mudança de status"""
        message = f"[SISTEMA] {username} alterou status para: {new_status}"
        self._safe_after(0, self._add_chat_message, message)
    
    def on_user_discovered(self, username, lat, lon, status, port):
        """Callback para descoberta de usuário - evita spam mostrando apenas primeira descoberta"""
        if username not in self.discovered_users:
            self.discovered_users.add(username)
            message = f"[SISTEMA] Usuário {username} descoberto ({status})"
            self._safe_after(0, self._add_chat_message, message)
    
    def reset_discovered_users(self):
        """Limpa a lista de usuários descobertos (útil para testes ou reset)"""
        self.discovered_users.clear()
        message = "[SISTEMA] Lista de usuários descobertos resetada"
        self._safe_after(0, self._add_chat_message, message)
