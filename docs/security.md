# Seguridad — Moodle Guardian

> Documento vivo. Threat-model lite + decisiones y procedimientos de seguridad.
> Creado: 2026-07-02.

## Cifrado del `moodle_token` at-rest ✅ (2026-07-02)

### Por qué
Guardamos el `moodle_token` de cada estudiante. Es un secreto: un token válido
da acceso a la cuenta Moodle del usuario. **Vence ~12 semanas** (`invalidtimedtoken`)
y también puede revocarse (`invalidtoken`, ej. cambio de contraseña), pero mientras
vive es plenamente usable. Una fuga de la DB expondría los tokens válidos de **todos
los usuarios a la vez** + PII → cifrarlo at-rest es el *gate* para salir al público.

### Cómo (Fernet en la frontera con la DB)
- **`src/infrastructure/security/token_cipher.py`** — `TokenCipher` sobre
  `MultiFernet` (AES-128-CBC + HMAC). La **primera** clave cifra; **todas** descifran
  (habilita rotación). Factory cacheada `get_token_cipher()` lee las claves de settings.
- **`PostgresUserRepository`** cifra en `save`/`update` y descifra en `_to_entity`.
  El dominio (`User.moodle_token: str`) y los casos de uso **siempre ven el token en
  claro**; nadie fuera del repo toca ciphertext.
- **Fallback legacy** en `decrypt`: si el valor no es un ciphertext Fernet válido, se
  asume texto plano heredado y se devuelve tal cual con un `warning` (sin imprimir el
  valor). Permite operar durante la transición. **Quitar una vez migrados todos.**
- La columna sigue siendo `String` (el ciphertext Fernet es base64 `gAAAA…`, ~140
  chars) → sin migración de esquema.

### Clave de cifrado (`TOKEN_ENCRYPTION_KEY`)
- Generar: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- Formato env: una clave, o varias separadas por coma para rotación
  (`clave_nueva,clave_vieja`) — la primera cifra.
- ⚠️ **Si se pierde la clave, los tokens cifrados son irrecuperables** (los usuarios
  deberían re-vincularse). Guardarla en el secret manager del entorno, nunca en el repo.
- ⚠️ **La MISMA clave debe estar en todos los entornos que tocan la DB** (local, worker,
  API en Render). Si el entorno desplegado no tiene la clave con que se cifró, la app
  falla al leer usuarios.

### Migración de tokens existentes
`scripts/encrypt_existing_tokens.py` — recorre `UserModel`, cifra los que aún están en
texto plano, saltea los ya cifrados (`TokenCipher.is_encrypted`). **Idempotente.**
Correr con: `python -m scripts.encrypt_existing_tokens`.

**Orden de despliegue seguro:**
1. Setear `TOKEN_ENCRYPTION_KEY` en el entorno desplegado (Render) + redeploy.
2. Recién entonces correr la migración contra la DB de producción.

### Rotación de clave (procedimiento)
1. Generar clave nueva. Setear `TOKEN_ENCRYPTION_KEY=nueva,vieja` (nueva primero).
2. Redeploy (la app ya descifra con ambas, cifra con la nueva).
3. Re-cifrar todo: correr `scripts/encrypt_existing_tokens.py`. ⚠️ Hoy el script solo
   cifra texto plano; para re-cifrar ciphertext viejo con la clave nueva hay que
   extenderlo (usar `MultiFernet.rotate`). Anotar como mejora si se rota en serio.
4. Quitar la clave vieja del env → `TOKEN_ENCRYPTION_KEY=nueva`.

## Checklist de seguridad (transversal, roadmap init. 5)
- [x] `moodle_token` cifrado at-rest + rotación de clave.
- [x] Token no se loguea (verificado; fallback legacy no imprime el valor).
- [ ] HTTPS en todo; auth/rate-limit en endpoints públicos.
- [ ] PII (chat_id, nombres, datos Moodle): retención, borrado a pedido, consentimiento.
- [ ] Manejo de secretos en secret manager (no en repo); `.env` fuera de VCS (ya gitignoreado).
- [ ] Detección de token muerto → avisar + relink (`docs/token-recovery.md`).

## Pendientes / deuda
- Quitar el fallback legacy de `TokenCipher.decrypt` cuando todos los tokens estén migrados.
- `moodle_token` value object con `__repr__` enmascarado (roadmap init. 5) — hoy el VO
  `src/domain/value_objects/moodle_token.py` está vacío.
- Rotación real: extender el script de migración para re-cifrar ciphertext con `MultiFernet.rotate`.
