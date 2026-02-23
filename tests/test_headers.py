from core.client import HTTPClient
from config.headers import get_dynamic_headers

client = HTTPClient()
print("Headers enviados:")
print(client.session.headers)

# Intenta un simple GET
html = client.get("https://www.buscalibre.cl/libros/arte", request_type="category")
print(f"\nStatus: {html is not None}")
if html:
    print(f"Tamaño respuesta: {len(html)} bytes")
else:
    print("No se obtuvo respuesta (posible bloqueo)")
