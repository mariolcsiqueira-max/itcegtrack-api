from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="ITCEGTrack API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def execute_query(conn, query, params=None, fetch=True):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(query, params)
    if fetch:
        results = cur.fetchall()
        cur.close()
        return [dict(r) for r in results]
    else:
        conn.commit()
        cur.close()
        return None

# ===== MODELS =====
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    name: str
    role: str = "tecnico"
    active: bool = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None

class ClientCreate(BaseModel):
    nome: str
    email: Optional[str] = None
    celular: Optional[str] = None
    empresa: Optional[str] = None
    cpfcnpj: Optional[str] = None
    rua: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    cep: Optional[str] = None
    estado: Optional[str] = None

class ServiceCreate(BaseModel):
    type: str
    type_label: Optional[str] = None
    client_name: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    price: float = 0
    equipment_number: Optional[str] = None
    observations: Optional[str] = None
    photo_plate: Optional[str] = None
    photo_equip: Optional[str] = None
    photo_equip_out: Optional[str] = None
    photo_equip_in: Optional[str] = None
    client_out: Optional[str] = None
    client_in: Optional[str] = None
    equipment_out: Optional[str] = None
    equipment_in: Optional[str] = None
    technician: Optional[str] = None
    role: Optional[str] = None

class LaudoCreate(BaseModel):
    client_name: Optional[str] = None
    vehicle_plate: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_brand: Optional[str] = None
    vehicle_model: Optional[str] = None
    photo_plate: Optional[str] = None
    photo_laudo: Optional[str] = None
    conclusion: Optional[str] = None
    technician: Optional[str] = None

class PricingCreate(BaseModel):
    technician: str
    service_type: str
    service_label: Optional[str] = None
    price: float = 0
    set_by: Optional[str] = None
    status: str = "pending"

class PaymentCreate(BaseModel):
    technician: str
    period_type: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    amount: float = 0
    paid: bool = False
    paid_by: Optional[str] = None

class SystemCostCreate(BaseModel):
    cost_per_user: float = 0
    cost_per_record: float = 0
    cost_per_laudo: float = 0
    set_by: Optional[str] = None

# ===== LOGIN =====
@app.post("/api/login")
def login(req: LoginRequest):
    conn = get_conn()
    try:
        users = execute_query(conn,
            "SELECT * FROM users WHERE username = %s AND password = %s AND active = TRUE",
            (req.username, req.password))
        if not users:
            raise HTTPException(status_code=401, detail="Usuario ou senha incorretos")
        user = users[0]
        return {"id": user["id"], "username": user["username"], "name": user["name"], "role": user["role"], "active": user["active"]}
    finally:
        conn.close()

# ===== USERS =====
@app.get("/api/users")
def get_users():
    conn = get_conn()
    try:
        return execute_query(conn, "SELECT * FROM users ORDER BY date_added DESC")
    finally:
        conn.close()

@app.post("/api/users")
def create_user(user: UserCreate):
    conn = get_conn()
    try:
        existing = execute_query(conn, "SELECT id FROM users WHERE username = %s", (user.username,))
        if existing:
            raise HTTPException(status_code=400, detail="Ja existe um usuario com este login")
        result = execute_query(conn,
            "INSERT INTO users (username, password, name, role, active) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (user.username, user.password, user.name, user.role, user.active))
        return result[0]
    finally:
        conn.close()

@app.put("/api/users/{user_id}")
def update_user(user_id: int, user: UserUpdate):
    conn = get_conn()
    try:
        existing = execute_query(conn, "SELECT * FROM users WHERE id = %s", (user_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="Usuario nao encontrado")
        current = existing[0]
        updates = []
        params = []
        for field in ["username", "password", "name", "role", "active"]:
            val = getattr(user, field)
            if val is not None:
                updates.append(f"{field} = %s")
                params.append(val)
        if not updates:
            return current
        params.append(user_id)
        result = execute_query(conn, f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING *", params)
        return result[0]
    finally:
        conn.close()

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    conn = get_conn()
    try:
        execute_query(conn, "DELETE FROM users WHERE id = %s", (user_id,), fetch=False)
        return {"success": True}
    finally:
        conn.close()

# ===== CLIENTS =====
@app.get("/api/clients")
def get_clients():
    conn = get_conn()
    try:
        return execute_query(conn, "SELECT * FROM clients ORDER BY date_added DESC")
    finally:
        conn.close()

@app.post("/api/clients")
def create_client(client: ClientCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            "INSERT INTO clients (nome, email, celular, empresa, cpfcnpj, rua, numero, complemento, bairro, cidade, cep, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
            (client.nome, client.email, client.celular, client.empresa, client.cpfcnpj, client.rua, client.numero, client.complemento, client.bairro, client.cidade, client.cep, client.estado))
        return result[0]
    finally:
        conn.close()

@app.put("/api/clients/{client_id}")
def update_client(client_id: int, client: ClientCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            "UPDATE clients SET nome=%s, email=%s, celular=%s, empresa=%s, cpfcnpj=%s, rua=%s, numero=%s, complemento=%s, bairro=%s, cidade=%s, cep=%s, estado=%s WHERE id = %s RETURNING *",
            (client.nome, client.email, client.celular, client.empresa, client.cpfcnpj, client.rua, client.numero, client.complemento, client.bairro, client.cidade, client.cep, client.estado, client_id))
        if not result:
            raise HTTPException(status_code=404, detail="Cliente nao encontrado")
        return result[0]
    finally:
        conn.close()

@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int):
    conn = get_conn()
    try:
        execute_query(conn, "DELETE FROM clients WHERE id = %s", (client_id,), fetch=False)
        return {"success": True}
    finally:
        conn.close()

# ===== SERVICES =====
@app.get("/api/services")
def get_services(technician: Optional[str] = None):
    conn = get_conn()
    try:
        if technician:
            return execute_query(conn, "SELECT * FROM services WHERE technician = %s ORDER BY date DESC", (technician,))
        return execute_query(conn, "SELECT * FROM services ORDER BY date DESC")
    finally:
        conn.close()

@app.post("/api/services")
def create_service(service: ServiceCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            """INSERT INTO services (type, type_label, client_name, vehicle_plate, vehicle_type, vehicle_brand, vehicle_model, price, equipment_number, observations, photo_plate, photo_equip, photo_equip_out, photo_equip_in, client_out, client_in, equipment_out, equipment_in, technician, role, synced)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE) RETURNING *""",
            (service.type, service.type_label, service.client_name, service.vehicle_plate, service.vehicle_type, service.vehicle_brand, service.vehicle_model, service.price, service.equipment_number, service.observations, service.photo_plate, service.photo_equip, service.photo_equip_out, service.photo_equip_in, service.client_out, service.client_in, service.equipment_out, service.equipment_in, service.technician, service.role))
        return result[0]
    finally:
        conn.close()

@app.put("/api/services/{service_id}")
def update_service(service_id: int, service: ServiceCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            """UPDATE services SET type=%s, type_label=%s, client_name=%s, vehicle_plate=%s, vehicle_type=%s, vehicle_brand=%s, vehicle_model=%s, price=%s, equipment_number=%s, observations=%s, photo_plate=%s, photo_equip=%s, photo_equip_out=%s, photo_equip_in=%s, client_out=%s, client_in=%s, equipment_out=%s, equipment_in=%s, technician=%s, role=%s, synced=TRUE WHERE id = %s RETURNING *""",
            (service.type, service.type_label, service.client_name, service.vehicle_plate, service.vehicle_type, service.vehicle_brand, service.vehicle_model, service.price, service.equipment_number, service.observations, service.photo_plate, service.photo_equip, service.photo_equip_out, service.photo_equip_in, service.client_out, service.client_in, service.equipment_out, service.equipment_in, service.technician, service.role, service_id))
        if not result:
            raise HTTPException(status_code=404, detail="Servico nao encontrado")
        return result[0]
    finally:
        conn.close()

@app.delete("/api/services/{service_id}")
def delete_service(service_id: int):
    conn = get_conn()
    try:
        execute_query(conn, "DELETE FROM services WHERE id = %s", (service_id,), fetch=False)
        return {"success": True}
    finally:
        conn.close()

# ===== LAUDOS =====
@app.get("/api/laudos")
def get_laudos(technician: Optional[str] = None):
    conn = get_conn()
    try:
        if technician:
            return execute_query(conn, "SELECT * FROM laudos WHERE technician = %s ORDER BY date DESC", (technician,))
        return execute_query(conn, "SELECT * FROM laudos ORDER BY date DESC")
    finally:
        conn.close()

@app.post("/api/laudos")
def create_laudo(laudo: LaudoCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            "INSERT INTO laudos (client_name, vehicle_plate, vehicle_type, vehicle_brand, vehicle_model, photo_plate, photo_laudo, conclusion, technician) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
            (laudo.client_name, laudo.vehicle_plate, laudo.vehicle_type, laudo.vehicle_brand, laudo.vehicle_model, laudo.photo_plate, laudo.photo_laudo, laudo.conclusion, laudo.technician))
        return result[0]
    finally:
        conn.close()

@app.delete("/api/laudos/{laudo_id}")
def delete_laudo(laudo_id: int):
    conn = get_conn()
    try:
        execute_query(conn, "DELETE FROM laudos WHERE id = %s", (laudo_id,), fetch=False)
        return {"success": True}
    finally:
        conn.close()

# ===== PRICING =====
@app.get("/api/pricing")
def get_pricing():
    conn = get_conn()
    try:
        return execute_query(conn, "SELECT * FROM pricing ORDER BY set_date DESC")
    finally:
        conn.close()

@app.post("/api/pricing")
def create_pricing(pricing: PricingCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            "INSERT INTO pricing (technician, service_type, service_label, price, set_by, status) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
            (pricing.technician, pricing.service_type, pricing.service_label, pricing.price, pricing.set_by, pricing.status))
        return result[0]
    finally:
        conn.close()

@app.put("/api/pricing/{pricing_id}")
def update_pricing(pricing_id: int, pricing: PricingCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            "UPDATE pricing SET technician=%s, service_type=%s, service_label=%s, price=%s, set_by=%s, status=%s WHERE id = %s RETURNING *",
            (pricing.technician, pricing.service_type, pricing.service_label, pricing.price, pricing.set_by, pricing.status, pricing_id))
        if not result:
            raise HTTPException(status_code=404, detail="Preco nao encontrado")
        return result[0]
    finally:
        conn.close()

@app.delete("/api/pricing/{pricing_id}")
def delete_pricing(pricing_id: int):
    conn = get_conn()
    try:
        execute_query(conn, "DELETE FROM pricing WHERE id = %s", (pricing_id,), fetch=False)
        return {"success": True}
    finally:
        conn.close()

# ===== PAYMENTS =====
@app.get("/api/payments")
def get_payments():
    conn = get_conn()
    try:
        return execute_query(conn, "SELECT * FROM payments ORDER BY paid_date DESC NULLS LAST")
    finally:
        conn.close()

@app.post("/api/payments")
def create_payment(payment: PaymentCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            "INSERT INTO payments (technician, period_type, period_start, period_end, amount, paid, paid_by, paid_date) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW()) RETURNING *",
            (payment.technician, payment.period_type, payment.period_start, payment.period_end, payment.amount, payment.paid, payment.paid_by))
        return result[0]
    finally:
        conn.close()

# ===== SYSTEM COSTS =====
@app.get("/api/system-costs")
def get_system_costs():
    conn = get_conn()
    try:
        costs = execute_query(conn, "SELECT * FROM system_costs ORDER BY set_date DESC LIMIT 1")
        if costs:
            return costs[0]
        return {"cost_per_user": 0, "cost_per_record": 0, "cost_per_laudo": 0}
    finally:
        conn.close()

@app.post("/api/system-costs")
def create_system_cost(cost: SystemCostCreate):
    conn = get_conn()
    try:
        result = execute_query(conn,
            "INSERT INTO system_costs (cost_per_user, cost_per_record, cost_per_laudo, set_by) VALUES (%s, %s, %s, %s) RETURNING *",
            (cost.cost_per_user, cost.cost_per_record, cost.cost_per_laudo, cost.set_by))
        return result[0]
    finally:
        conn.close()

# ===== SYNC =====
@app.post("/api/sync")
def sync_services(services: List[dict]):
    conn = get_conn()
    try:
        synced_count = 0
        for svc in services:
            if not svc.get("synced"):
                execute_query(conn,
                    """INSERT INTO services (type, type_label, client_name, vehicle_plate, vehicle_type, vehicle_brand, vehicle_model, price, equipment_number, observations, photo_plate, photo_equip, photo_equip_out, photo_equip_in, client_out, client_in, equipment_out, equipment_in, technician, role, synced)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)""",
                    (svc.get("type"), svc.get("type_label"), svc.get("client_name"), svc.get("vehicle_plate"), svc.get("vehicle_type"), svc.get("vehicle_brand"), svc.get("vehicle_model"), svc.get("price", 0), svc.get("equipment_number"), svc.get("observations"), svc.get("photo_plate"), svc.get("photo_equip"), svc.get("photo_equip_out"), svc.get("photo_equip_in"), svc.get("client_out"), svc.get("client_in"), svc.get("equipment_out"), svc.get("equipment_in"), svc.get("technician"), svc.get("role")),
                    fetch=False)
                synced_count += 1
        return {"synced": synced_count}
    finally:
        conn.close()

@app.get("/")
def root():
    return {"status": "ITCEGTrack API running", "version": "1.0.0"}