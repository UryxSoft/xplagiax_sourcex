# 🔄 GUÍA DE MIGRACIÓN - De Código Legacy a Código Refactorizado

## 📋 Checklist de Migración

### Pre-Migración
- [ ] Backup completo del código actual
- [ ] Backup de base de datos (Redis, FAISS, SQLite)
- [ ] Documentar configuración actual
- [ ] Notificar al equipo del mantenimiento

### Migración
- [ ] Copiar archivos nuevos
- [ ] Configurar .env
- [ ] Migrar datos (si es necesario)
- [ ] Testing en staging
- [ ] Deployment en producción

### Post-Migración
- [ ] Verificar health checks
- [ ] Monitorear logs
- [ ] Validar endpoints
- [ ] Actualizar documentación del equipo

---

## 🚀 Opción 1: Migración Completa (Recomendada)

### Paso 1: Backup

```bash
# Backup de código actual
cd /path/to/proyecto
tar -czf backup_$(date +%Y%m%d).tar.gz .

# Backup de datos
docker exec academic_search_app tar -czf /app/backups/data_backup_$(date +%Y%m%d).tar.gz /app/data
docker cp academic_search_app:/app/backups/data_backup_$(date +%Y%m%d).tar.gz ./

# Backup de Redis
docker exec academic_search_redis redis-cli --rdb /data/dump_backup.rdb
docker cp academic_search_redis:/data/dump_backup.rdb ./
```

### Paso 2: Copiar Archivos Nuevos

```bash
# Copiar archivos refactorizados
cp /refactored_app/app.py ./
cp /refactored_app/auth.py ./
cp /refactored_app/cors_config.py ./
cp /refactored_app/.env.example ./

# Crear estructura de blueprints
mkdir -p blueprints
cp /refactored_app/blueprints/*.py ./blueprints/

# Copiar README y docs
cp /refactored_app/README.md ./
cp /refactored_app/REFACTORING_SUMMARY.md ./docs/
```

### Paso 3: Configurar Entorno

```bash
# Copiar .env y configurar
cp .env.example .env

# Generar secrets
echo "ADMIN_API_KEY=$(openssl rand -base64 48)" >> .env
echo "FLASK_SECRET_KEY=$(openssl rand -base64 48)" >> .env
echo "REDIS_PASSWORD=$(openssl rand -base64 32)" >> .env

# Configurar CORS
echo "ALLOWED_ORIGINS=https://yourdomain.com" >> .env

# Editar manualmente
nano .env
```

### Paso 4: Actualizar Imports

Si tienes archivos que importan desde `app.py`, actualizar:

```python
# ANTES
from app import create_app

# DESPUÉS (sigue igual)
from app import create_app

# Los blueprints se importan dentro de app.py
```

### Paso 5: Testing en Staging

```bash
# Construir
docker-compose build

# Iniciar en modo test
docker-compose up

# Verificar health
curl http://localhost:5000/api/health

# Verificar autenticación
curl -H "X-API-Key: $(grep ADMIN_API_KEY .env | cut -d= -f2)" \
  -X POST http://localhost:5000/api/faiss/save

# Probar búsqueda
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "machine learning",
      "en",
      [["p1", "1", "Neural networks are models"]]
    ]
  }'
```

### Paso 6: Deployment en Producción

```bash
# Detener servicio actual
docker-compose down

# Backup final
docker cp academic_search_app:/app/data ./data_final_backup

# Iniciar con nuevo código
docker-compose up -d --build

# Monitorear logs
docker-compose logs -f app

# Verificar endpoints críticos
curl https://api.yourdomain.com/api/health
```

---

## 🔄 Opción 2: Migración Gradual (Blue-Green Deployment)

### Paso 1: Deploy Paralelo

```bash
# Renombrar servicios actuales
docker-compose -p xplagiax_old up -d

# Deploy nuevo código en puerto diferente
# docker-compose.yml (nuevo)
services:
  app:
    ports:
      - "5001:5000"  # Puerto diferente

docker-compose -p xplagiax_new up -d --build
```

### Paso 2: Testing en Paralelo

```bash
# Viejo (puerto 5000)
curl http://localhost:5000/api/health

# Nuevo (puerto 5001)
curl http://localhost:5001/api/health

# Comparar respuestas
diff <(curl -s http://localhost:5000/api/faiss/stats) \
     <(curl -s http://localhost:5001/api/faiss/stats)
```

### Paso 3: Migrar Tráfico Gradualmente

```nginx
# nginx.conf
upstream backend {
    server localhost:5000 weight=9;  # 90% tráfico viejo
    server localhost:5001 weight=1;  # 10% tráfico nuevo
}

# Después de validar:
upstream backend {
    server localhost:5000 weight=5;  # 50/50
    server localhost:5001 weight=5;
}

# Finalmente:
upstream backend {
    server localhost:5001 weight=1;  # 100% nuevo
}
```

### Paso 4: Apagar Sistema Viejo

```bash
docker-compose -p xplagiax_old down
docker-compose -p xplagiax_new down

# Renombrar a producción
mv docker-compose.yml docker-compose.yml.old
mv docker-compose.new.yml docker-compose.yml

docker-compose up -d
```

---

## 🔧 Opción 3: Migración Selectiva (Solo Críticos)

Si no puedes hacer migración completa, aplicar solo fixes críticos:

### 1. Agregar Autenticación

```python
# auth.py (copiar completo)
# En app.py actual, agregar:

from auth import require_api_key

# Proteger endpoints:
@app.route('/api/faiss/clear', methods=['POST'])
@require_api_key  # ✅ Agregar esta línea
def faiss_clear():
    ...
```

### 2. Fix CORS

```python
# En app.py actual, reemplazar:

# ANTES
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv("ALLOWED_ORIGINS", "*").split(","),
        ...
    }
})

# DESPUÉS
from cors_config import setup_cors
setup_cors(app)
```

### 3. Validar Secrets

```python
# En app.py, al inicio de create_app():

from auth import validate_api_keys_on_startup

warnings = validate_api_keys_on_startup()
if warnings:
    for warning in warnings:
        logger.warning(warning)
```

---

## ⚠️ PROBLEMAS COMUNES Y SOLUCIONES

### Problema 1: Endpoints No Funcionan

**Síntoma**: 404 en todos los endpoints

**Solución**:
```python
# Verificar que blueprints están registrados
print(app.url_map)  # Debe mostrar todas las rutas

# Verificar url_prefix
search_bp = Blueprint('search', __name__, url_prefix='/api')  # ✅ Correcto
```

### Problema 2: Autenticación Falla

**Síntoma**: 500 error en endpoints protegidos

**Solución**:
```bash
# Verificar que ADMIN_API_KEY está configurado
grep ADMIN_API_KEY .env

# Si está vacío, generar uno:
openssl rand -base64 48 >> .env
```

### Problema 3: CORS Errors

**Síntoma**: Navegador bloquea requests

**Solución**:
```bash
# Verificar ALLOWED_ORIGINS
grep ALLOWED_ORIGINS .env

# Debe contener el dominio del frontend:
ALLOWED_ORIGINS=https://frontend.com,http://localhost:3000

# Reiniciar servicio
docker-compose restart app
```

### Problema 4: Redis Connection Refused

**Síntoma**: "Redis no disponible"

**Solución**:
```bash
# Verificar que Redis está corriendo
docker-compose ps redis

# Verificar password
docker exec academic_search_redis redis-cli -a $(grep REDIS_PASSWORD .env | cut -d= -f2) PING

# Debe retornar: PONG
```

### Problema 5: FAISS Index Corrupto

**Síntoma**: "FAISS corrupted" en health check

**Solución**:
```bash
# Limpiar y reconstruir
curl -H "X-API-Key: your-key" -X POST http://localhost:5000/api/faiss/clear

# O restaurar desde backup
docker cp ./data_backup/faiss_index.index academic_search_app:/app/data/
docker-compose restart app
```

---

## 📊 Validación Post-Migración

### Checklist de Validación

```bash
# 1. Health check
curl http://localhost:5000/api/health | jq .

# Debe retornar:
# {
#   "status": "healthy",
#   "redis": "connected",
#   "faiss": { "total_papers": N }
# }

# 2. Autenticación funciona
curl -H "X-API-Key: wrong-key" -X POST http://localhost:5000/api/faiss/save
# Debe retornar 403

curl -H "X-API-Key: $(grep ADMIN_API_KEY .env | cut -d= -f2)" \
  -X POST http://localhost:5000/api/faiss/save
# Debe retornar 200

# 3. Búsqueda funciona
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{"data": ["test", "en", [["p1", "1", "test text"]]]}'
# Debe retornar resultados

# 4. FAISS funciona
curl http://localhost:5000/api/faiss/stats
# Debe mostrar papers indexados

# 5. Métricas funcionan
curl http://localhost:5000/api/metrics
# Debe retornar formato Prometheus
```

### Monitoreo Inicial (Primeras 24h)

```bash
# Logs en tiempo real
docker-compose logs -f app | grep ERROR

# Métricas cada 5 minutos
watch -n 300 'curl -s http://localhost:5000/api/health | jq .'

# Errores en últimas 24h
docker-compose logs --since 24h app | grep ERROR | wc -l
```

---

## 🔙 Rollback (Si Algo Sale Mal)

### Plan de Rollback

```bash
# 1. Detener nuevo código
docker-compose down

# 2. Restaurar código anterior
tar -xzf backup_$(date +%Y%m%d).tar.gz

# 3. Restaurar datos
docker cp ./data_final_backup academic_search_app:/app/data

# 4. Restaurar Redis
docker cp ./dump_backup.rdb academic_search_redis:/data/dump.rdb
docker exec academic_search_redis redis-cli SHUTDOWN SAVE
docker-compose start redis

# 5. Iniciar sistema anterior
docker-compose up -d

# 6. Verificar
curl http://localhost:5000/api/health
```

---

## 📝 Comunicación con el Equipo

### Email Template

```
Asunto: Migración a Código Refactorizado v2.0

Hola equipo,

Realizaremos la migración al código refactorizado el [FECHA] a las [HORA].

CAMBIOS PRINCIPALES:
- ✅ Arquitectura modular (blueprints)
- ✅ Autenticación en endpoints administrativos
- ✅ CORS seguro por default
- ✅ Mejor documentación

IMPACTO:
- Downtime estimado: 5-10 minutos
- Nuevos endpoints requieren X-API-Key header
- Sin cambios en API pública

ACCIÓN REQUERIDA:
1. Actualizar scripts que usen endpoints admin
2. Agregar header: X-API-Key: [KEY_PROPORCIONADA]
3. Validar en staging antes del deploy

DOCUMENTACIÓN:
- README: /docs/README.md
- Migración: /docs/MIGRATION_GUIDE.md

Saludos,
[TU NOMBRE]
```

---

## ✅ Checklist Final

### Pre-Deploy
- [ ] Código probado en staging
- [ ] Backups completados
- [ ] Team notificado
- [ ] .env configurado correctamente
- [ ] ADMIN_API_KEY compartida con admins

### Deploy
- [ ] docker-compose build exitoso
- [ ] docker-compose up sin errores
- [ ] Health check pasa
- [ ] Autenticación funciona
- [ ] Búsquedas funcionan
- [ ] FAISS está operativo

### Post-Deploy
- [ ] Monitoreo activo (primeras 2 horas)
- [ ] Logs sin errores críticos
- [ ] Performance similar o mejor
- [ ] Usuarios reportan funcionamiento normal
- [ ] Documentación actualizada

---

## 🎯 RESUMEN

### Tiempo Estimado

- **Opción 1 (Completa)**: 2-3 horas
- **Opción 2 (Gradual)**: 1 día
- **Opción 3 (Selectiva)**: 30 minutos

### Recomendación

Para **producción crítica**: Opción 2 (Blue-Green)
Para **staging/desarrollo**: Opción 1 (Completa)
Para **fix urgente**: Opción 3 (Selectiva)

### Soporte

**¿Problemas durante la migración?**
- Slack: #xplagiax-dev
- Email: devops@xplagiax.com
- Escalación: CTO

---

**Éxito con la migración! 🚀**