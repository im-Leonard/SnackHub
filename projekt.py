import flet as ft
import mysql.connector
from datetime import datetime, timedelta
import hashlib

# Datenbank-Verbindung
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",  # Anpassen
        password="",  # Anpassen
        database="schul_kantine"
    )

class KantineApp:
    def __init__(self):
        self.current_user = None
        self.user_role = None
        
    def main(self, page: ft.Page):
        page.title = "Schulkantine Manager"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 0
        page.bgcolor = "#f5f5f5"
        
        self.page = page
        
        # Login View
        def show_login():
            username_field = ft.TextField(
                label="Benutzername",
                width=300,
                prefix_icon=ft.icons.PERSON,
                border_color="#2196F3"
            )
            password_field = ft.TextField(
                label="Passwort",
                password=True,
                can_reveal_password=True,
                width=300,
                prefix_icon=ft.icons.LOCK,
                border_color="#2196F3"
            )
            error_text = ft.Text(color="red", size=12)
            
            role_dropdown = ft.Dropdown(
                label="Anmelden als",
                width=300,
                options=[
                    ft.dropdown.Option("schueler", "Schüler"),
                    ft.dropdown.Option("kantine", "Kantine"),
                    ft.dropdown.Option("admin", "Administrator")
                ],
                value="schueler",
                border_color="#2196F3"
            )
            
            def login_clicked(e):
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    
                    password_hash = hashlib.sha256(password_field.value.encode()).hexdigest()
                    
                    cursor.execute(
                        "SELECT * FROM users WHERE username = %s AND password_hash = %s AND role = %s",
                        (username_field.value, password_hash, role_dropdown.value)
                    )
                    user = cursor.fetchone()
                    
                    if user:
                        self.current_user = user
                        self.user_role = user['role']
                        
                        if self.user_role == 'schueler':
                            show_student_view()
                        elif self.user_role == 'kantine':
                            show_kantine_view()
                        else:
                            show_admin_view()
                    else:
                        error_text.value = "Ungültige Anmeldedaten!"
                        page.update()
                    
                    cursor.close()
                    conn.close()
                except Exception as ex:
                    error_text.value = f"Fehler: {str(ex)}"
                    page.update()
            
            login_container = ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Icon(ft.icons.RESTAURANT_MENU, size=80, color="white"),
                        bgcolor="#FF5722",
                        width=150,
                        height=150,
                        border_radius=75,
                        alignment=ft.alignment.center,
                    ),
                    ft.Text("Schulkantine Manager", size=32, weight=ft.FontWeight.BOLD, color="#2196F3"),
                    ft.Text("Willkommen zurück!", size=16, color="#666"),
                    ft.Container(height=20),
                    role_dropdown,
                    username_field,
                    password_field,
                    error_text,
                    ft.Container(height=10),
                    ft.ElevatedButton(
                        "Anmelden",
                        on_click=login_clicked,
                        width=300,
                        height=50,
                        style=ft.ButtonStyle(
                            color="white",
                            bgcolor="#2196F3",
                        )
                    ),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15),
                padding=50,
                bgcolor="white",
                border_radius=15,
                shadow=ft.BoxShadow(blur_radius=15, color="#00000020")
            )
            
            page.controls.clear()
            page.add(
                ft.Container(
                    content=login_container,
                    alignment=ft.alignment.center,
                    expand=True,
                )
            )
            page.update()
        
        # Schüler View
        def show_student_view():
            def show_voting():
                voting_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    
                    two_weeks = datetime.now() + timedelta(weeks=2)
                    cursor.execute("""
                        SELECT p.*, m.name, m.description 
                        FROM polls p 
                        JOIN meals m ON p.meal_id = m.meal_id
                        WHERE p.end_date >= %s
                        ORDER BY p.start_date
                    """, (datetime.now(),))
                    polls = cursor.fetchall()
                    
                    for poll in polls:
                        # Votes zählen
                        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE meal_id = %s", (poll['meal_id'],))
                        vote_count = cursor.fetchone()['count']
                        
                        poll_card = ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.icons.RESTAURANT, color="#FF5722"),
                                    ft.Text(poll['name'], size=18, weight=ft.FontWeight.BOLD),
                                ]),
                                ft.Text(poll['description'], color="#666"),
                                ft.Text(f"Zeitraum: {poll['start_date']} - {poll['end_date']}", size=12, color="#999"),
                                ft.Text(f"Aktuelle Stimmen: {vote_count}", size=14, color="#4CAF50", weight=ft.FontWeight.BOLD),
                                ft.ElevatedButton(
                                    "Abstimmen",
                                    bgcolor="#4CAF50",
                                    color="white",
                                    on_click=lambda e, meal_id=poll['meal_id']: vote_for_meal(meal_id)
                                )
                            ]),
                            bgcolor="white",
                            padding=20,
                            border_radius=10,
                            margin=10,
                            shadow=ft.BoxShadow(blur_radius=5, color="#00000010")
                        )
                        voting_list.controls.append(poll_card)
                    
                    cursor.close()
                    conn.close()
                except Exception as ex:
                    voting_list.controls.append(ft.Text(f"Fehler: {str(ex)}", color="red"))
                
                content_area.content = ft.Container(
                    content=ft.Column([
                        ft.Text("Abstimmungen", size=28, weight=ft.FontWeight.BOLD, color="#2196F3"),
                        ft.Text("Stimme für dein Lieblingsgericht in 2 Wochen!", color="#666"),
                        ft.Divider(),
                        voting_list
                    ]),
                    padding=20,
                    expand=True
                )
                page.update()
            
            def vote_for_meal(meal_id):
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO orders (user_id, meal_id, quantity, is_paid, created_at) VALUES (%s, %s, 1, 0, %s)",
                        (self.current_user['user_id'], meal_id, datetime.now())
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    show_success_dialog("Erfolgreich abgestimmt!")
                    show_voting()
                except Exception as ex:
                    show_error_dialog(f"Fehler: {str(ex)}")
            
            def show_preorder():
                meal_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM meals WHERE date_available >= %s ORDER BY date_available", (datetime.now(),))
                    meals = cursor.fetchall()
                    
                    for meal in meals:
                        meal_card = ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.icons.FASTFOOD, color="#FF9800"),
                                    ft.Text(meal['name'], size=18, weight=ft.FontWeight.BOLD),
                                ]),
                                ft.Text(meal['description'], color="#666"),
                                ft.Text(f"Verfügbar am: {meal['date_available']}", size=12, color="#999"),
                                ft.ElevatedButton(
                                    "Vorbestellen",
                                    bgcolor="#FF9800",
                                    color="white",
                                    on_click=lambda e, meal_id=meal['meal_id']: preorder_meal(meal_id)
                                )
                            ]),
                            bgcolor="white",
                            padding=20,
                            border_radius=10,
                            margin=10,
                            shadow=ft.BoxShadow(blur_radius=5, color="#00000010")
                        )
                        meal_list.controls.append(meal_card)
                    
                    cursor.close()
                    conn.close()
                except Exception as ex:
                    meal_list.controls.append(ft.Text(f"Fehler: {str(ex)}", color="red"))
                
                content_area.content = ft.Container(
                    content=ft.Column([
                        ft.Text("Vorbestellung", size=28, weight=ft.FontWeight.BOLD, color="#2196F3"),
                        ft.Text("Bestelle dein Essen vor und bezahle vor Ort!", color="#666"),
                        ft.Divider(),
                        meal_list
                    ]),
                    padding=20,
                    expand=True
                )
                page.update()
            
            def preorder_meal(meal_id):
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO orders (user_id, meal_id, quantity, is_paid, created_at) VALUES (%s, %s, 1, 0, %s)",
                        (self.current_user['user_id'], meal_id, datetime.now())
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    show_success_dialog("Erfolgreich vorbestellt! Bitte bezahle vor Ort.")
                    show_preorder()
                except Exception as ex:
                    show_error_dialog(f"Fehler: {str(ex)}")
            
            def show_feedback():
                feedback_text = ft.TextField(
                    label="Dein Feedback",
                    multiline=True,
                    min_lines=5,
                    max_lines=10,
                    border_color="#2196F3"
                )
                
                meal_dropdown = ft.Dropdown(
                    label="Gericht auswählen",
                    width=300,
                    border_color="#2196F3"
                )
                
                rating_slider = ft.Slider(
                    min=1,
                    max=5,
                    divisions=4,
                    label="Bewertung: {value}",
                    value=3
                )
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT meal_id, name FROM meals")
                    meals = cursor.fetchall()
                    meal_dropdown.options = [ft.dropdown.Option(str(m['meal_id']), m['name']) for m in meals]
                    cursor.close()
                    conn.close()
                except Exception as ex:
                    pass
                
                def submit_feedback(e):
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO feedback (user_id, meal_id, comment, rating, created_at) VALUES (%s, %s, %s, %s, %s)",
                            (self.current_user['user_id'], int(meal_dropdown.value), feedback_text.value, int(rating_slider.value), datetime.now())
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        show_success_dialog("Feedback erfolgreich gesendet!")
                        feedback_text.value = ""
                        rating_slider.value = 3
                        page.update()
                    except Exception as ex:
                        show_error_dialog(f"Fehler: {str(ex)}")
                
                content_area.content = ft.Container(
                    content=ft.Column([
                        ft.Text("Feedback", size=28, weight=ft.FontWeight.BOLD, color="#2196F3"),
                        ft.Text("Teile deine Meinung mit der Kantine!", color="#666"),
                        ft.Divider(),
                        meal_dropdown,
                        ft.Text("Bewertung:", size=16, weight=ft.FontWeight.BOLD),
                        rating_slider,
                        feedback_text,
                        ft.ElevatedButton(
                            "Feedback senden",
                            bgcolor="#9C27B0",
                            color="white",
                            on_click=submit_feedback,
                            width=200
                        )
                    ], scroll=ft.ScrollMode.AUTO),
                    padding=20,
                    expand=True
                )
                page.update()
            
            # Navigation
            nav_rail = ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                min_extended_width=200,
                destinations=[
                    ft.NavigationRailDestination(
                        icon=ft.icons.HOW_TO_VOTE_OUTLINED,
                        selected_icon=ft.icons.HOW_TO_VOTE,
                        label="Abstimmen"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.SHOPPING_CART_OUTLINED,
                        selected_icon=ft.icons.SHOPPING_CART,
                        label="Vorbestellen"
                    ),
                    ft.NavigationRailDestination(
                        icon=ft.icons.FEEDBACK_OUTLINED,
                        selected_icon=ft.icons.FEEDBACK,
                        label="Feedback"
                    ),
                ],
                on_change=lambda e: handle_nav_change(e.control.selected_index),
                bgcolor="#2196F3",
                selected_label_text_style=ft.TextStyle(color="white"),
                unselected_label_text_style=ft.TextStyle(color="#B3E5FC")
            )
            
            def handle_nav_change(index):
                if index == 0:
                    show_voting()
                elif index == 1:
                    show_preorder()
                elif index == 2:
                    show_feedback()
            
            content_area = ft.Container(expand=True)
            
            page.controls.clear()
            page.add(
                ft.Row([
                    nav_rail,
                    ft.VerticalDivider(width=1),
                    content_area
                ], expand=True)
            )
            show_voting()
            page.update()
        
        # Kantine View
        def show_kantine_view():
            def show_poll_results():
                results_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    
                    cursor.execute("""
                        SELECT m.name, m.description, COUNT(o.order_id) as votes
                        FROM meals m
                        LEFT JOIN orders o ON m.meal_id = o.meal_id
                        GROUP BY m.meal_id
                        ORDER BY votes DESC
                    """)
                    results = cursor.fetchall()
                    
                    for result in results:
                        result_card = ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.icons.RESTAURANT, color="#FF5722", size=40),
                                ft.Column([
                                    ft.Text(result['name'], size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(result['description'], color="#666"),
                                ], expand=True),
                                ft.Container(
                                    content=ft.Text(f"{result['votes']}", size=24, weight=ft.FontWeight.BOLD, color="white"),
                                    bgcolor="#4CAF50",
                                    padding=15,
                                    border_radius=50,
                                    width=70,
                                    height=70,
                                    alignment=ft.alignment.center
                                )
                            ]),
                            bgcolor="white",
                            padding=20,
                            border_radius=10,
                            margin=10,
                            shadow=ft.BoxShadow(blur_radius=5, color="#00000010")
                        )
                        results_list.controls.append(result_card)
                    
                    cursor.close()
                    conn.close()
                except Exception as ex:
                    results_list.controls.append(ft.Text(f"Fehler: {str(ex)}", color="red"))
                
                content_area.content = ft.Container(
                    content=ft.Column([
                        ft.Text("Abstimmungsergebnisse", size=28, weight=ft.FontWeight.BOLD, color="#2196F3"),
                        ft.Text("Übersicht der Stimmen für alle Gerichte", color="#666"),
                        ft.Divider(),
                        results_list
                    ]),
                    padding=20,
                    expand=True
                )
                page.update()
            
            def show_feedbacks():
                feedback_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
                
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    
                    cursor.execute("""
                        SELECT f.*, m.name as meal_name, u.username
                        FROM feedback f
                        JOIN meals m ON f.meal_id = m.meal_id
                        JOIN users u ON f.user_id = u.user_id
                        ORDER BY f.created_at DESC
                    """)
                    feedbacks = cursor.fetchall()
                    
                    for fb in feedbacks:
                        stars = "⭐" * fb['rating']
                        feedback_card = ft.Container(
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.icons.PERSON, color="#9C27B0"),
                                    ft.Text(fb['username'], weight=ft.FontWeight.BOLD),
                                    ft.Text(f"→ {fb['meal_name']}", color="#666"),
                                ]),
                                ft.Text(stars, size=18),
                                ft.Text(fb['comment'], color="#333"),
                                ft.Text(f"Datum: {fb['created_at']}", size=11, color="#999"),
                            ]),
                            bgcolor="white",
                            padding=20,
                            border_radius=10,
                            margin=10,
                            shadow=ft.BoxShadow(blur_radius=5, color="#00000010")
                        )
                        feedback_list.controls.append(feedback_card)
                    
                    cursor.close()
                    conn.close()
                except Exception as ex:
                    feedback_list.controls.append(ft.Text(f"Fehler: {str(ex)}", color="red"))
                
                content_area.content = ft.Container(
                    content=ft.Column([
                        ft.Text("Feedback Übersicht", size=28, weight=ft.FontWeight.BOLD, color="#2196F3"),
                        ft.Text("Alle Rückmeldungen von Schülern", color="#666"),
                        ft.Divider(),
                        feedback_list
                    ]),
                    padding=20,
                    expand=True
                )
                page.update()
            
            def show_profile():
                meal_name = ft.TextField(label="Gericht Name", border_color="#2196F3")
                meal_desc = ft.TextField(label="Beschreibung", multiline=True, border_color="#2196F3")
                meal_date = ft.TextField(label="Verfügbar am (YYYY-MM-DD)", border_color="#2196F3")
                
                def add_meal(e):
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO meals (name, description, date_available) VALUES (%s, %s, %s)",
                            (meal_name.value, meal_desc.value, meal_date.value)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        show_success_dialog("Gericht erfolgreich hinzugefügt!")
                        meal_name.value = ""
                        meal_desc.value = ""
                        meal_date.value = ""
                        page.update()
                    except Exception as ex:
                        show_error_dialog(f"Fehler: {str(ex)}")
                
                content_area.content = ft.Container(
                    content=ft.Column([
                        ft.Text("Kantinen-Profil", size=28, weight=ft.FontWeight.BOLD, color="#2196F3"),
                        ft.Text("Verwalte deine Gerichte", color="#666"),
                        ft.Divider(),
                        ft.Text("Neues Gericht hinzufügen:", size=20, weight=ft.FontWeight.BOLD),
                        meal_name,
                        meal_desc,
                        meal_date,
                        ft.ElevatedButton(
                            "Gericht hinzufügen",
                            bgcolor="#FF5722",
                            color="white",
                            on_click=add_meal,
                            width=200
                        )
                    ], scroll=ft.ScrollMode.AUTO),
                    padding=20,
                    expand=True
                )
                page.update()
            
            nav_rail = ft.NavigationRail(
                selected_index=0,
                label_type=ft.NavigationRailLabelType.ALL,
                min_width=100,
                destinations=[
                    ft.NavigationRailDestination(icon=ft.icons.POLL, label="Abstimmungen"),
                    ft.NavigationRailDestination(icon=ft.icons.FEEDBACK, label="Feedbacks"),
                    ft.NavigationRailDestination(icon=ft.icons.RESTAURANT_MENU, label="Profil"),
                ],
                on_change=lambda e: handle_kantine_nav(e.control.selected_index),
                bgcolor="#FF5722"
            )
            
            def handle_kantine_nav(index):
                if index == 0:
                    show_poll_results()
                elif index == 1:
                    show_feedbacks()
                elif index == 2:
                    show_profile()
            
            content_area = ft.Container(expand=True)
            
            page.controls.clear()
            page.add(
                ft.Row([nav_rail, ft.VerticalDivider(width=1), content_area], expand=True)
            )
            show_poll_results()
            page.update()
        
        # Admin View
        def show_admin_view():
            content_area.content = ft.Container(
                content=ft.Column([
                    ft.Text("Administrator Panel", size=28, weight=ft.FontWeight.BOLD, color="#2196F3"),
                    ft.Text("Verwalte Benutzer und System", color="#666"),
                    ft.Divider(),
                    ft.Text("Admin-Funktionen werden hier implementiert...", size=16)
                ]),
                padding=20
            )
            
            content_area = ft.Container(expand=True)
            page.controls.clear()
            page.add(content_area)
            page.update()
        
        # Hilfsfunktionen
        def show_success_dialog(message):
            dlg = ft.AlertDialog(
                title=ft.Text("Erfolg!"),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))],
            )
            page.dialog = dlg
            dlg.open = True
            page.update()
        
        def show_error_dialog(message):
            dlg = ft.AlertDialog(
                title=ft.Text("Fehler!"),
                content=ft.Text(message),
                actions=[ft.TextButton("OK", on_click=lambda e: close_dialog(dlg))],
            )
            page.dialog = dlg
            dlg.open = True
            page.update()
        
        def close_dialog(dialog):
            dialog.open = False
            page.update()
        
        # Start mit Login
        show_login()

if __name__ == "__main__":
    app = KantineApp()
    ft.app(target=app.main)