# Aigües de Barcelona (2Captcha) para Home Assistant

Este `custom_component` permite importar los datos de [Aigües de Barcelona](https://www.aiguesdebarcelona.cat/) en [Home Assistant](https://www.home-assistant.io/).

Puedes ver el consumo de agua que has hecho directamente en Home Assistant, y con esa información también puedes crear tus propias automatizaciones y avisos :)

Si te gusta el proyecto, dale a **Star** !

## Requisitos

Esta integración requiere una cuenta de [2Captcha](https://2captcha.com/) para resolver automáticamente el CAPTCHA de inicio de sesión.

- Regístrate en [2Captcha](https://2captcha.com/) y obtén tu API Key
- El coste es mínimo (aproximadamente $0.003 por resolución de CAPTCHA)
- La integración resuelve el CAPTCHA automáticamente cuando es necesario

## Uso

Esta integración expone un `sensor` con el último valor disponible de la lectura de agua del día de hoy.
La lectura que se muestra, puede estar demorada **hasta 4 días o más** (normalmente es 1-2 días).

La información se consulta **cada 8 horas** para no sobresaturar el servicio.

## Instalación

1. Via [HACS](https://hacs.xyz/), busca e instala este componente personalizado.

[![Install repository](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=albertparis&repository=hass-aigues-barcelona-2captcha&category=integration)

2. Cuando lo tengas descargado, agrega la integración en Home Assistant.

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start?domain=aigues_barcelona)

3. Durante la configuración, necesitarás proporcionar:
   - Tu NIF/NIE (usuario de Aigües de Barcelona)
   - Tu contraseña
   - Tu API Key de 2Captcha

## Actualización desde versiones anteriores

**⚠️ Cambio disruptivo en la versión actual**

Si actualizas desde una versión anterior, necesitarás realizar los siguientes pasos:

1. **Remover el sensor del Panel de Energía**: Ve a Configuración → Energía → Tu panel de energía → Remueve la fuente de agua existente.
2. **Limpiar estadísticas antiguas** (opcional): Ve a Configuración → Desarrollador → Estadísticas y elimina las estadísticas del sensor `sensor.contador_*`.
3. **Agregar la nueva fuente**: Una vez actualizado, vuelve al Panel de Energía y agrega la nueva fuente de agua.

Esto es necesario porque el ID de las estadísticas cambió de `sensor.contador_*` a `aigues_barcelona:*_consumption` para una mejor compatibilidad.

## Servicios

### `aigues_barcelona.reset_and_refresh_data`

Este servicio permite limpiar las estadísticas almacenadas y volver a importar los datos históricos. Útil si los datos del panel de Energía muestran valores incorrectos.

## Panel de Energía

Esta integración es compatible con el [Panel de Energía](https://www.home-assistant.io/docs/energy/) de Home Assistant. El sensor de agua se puede agregar directamente como fuente de agua.

### Costes desde las facturas

Activa **Importar facturas** en *Ajustes → Dispositivos y servicios → Aigües de Barcelona → Configurar*. La integración importa cada factura como la estadística `aigues_barcelona:<contrato>_cost` (en EUR), que puedes elegir en la fuente de agua con la opción *Usar una entidad que haga seguimiento de los costes totales*.

Cada factura se reparte por horas dentro de su periodo de facturación:

- La parte fija (cuota de servicio, tasas de residuos TMTR/TRR...) se reparte por igual entre todas las horas.
- La parte variable (consumo, canon del agua, alcantarillado y su IVA) sigue el consumo horario importado. Las horas sin datos de consumo reciben una parte igual.

Los costes solo se importan por meses completos: el mes en que acaba la última factura se importa cuando la siguiente factura lo completa, así que ningún mes muestra un coste parcial. Las facturas rectificativas y abonos no se tienen en cuenta: si dos facturas se solapan, se avisa en el registro. Las facturas se consultan una vez al día. Requiere Home Assistant 2024.11 o posterior.

## Ayuda

No soy un experto en Home Assistant, hay conceptos que son nuevos para mí en cuanto a la parte Developer. Así que puede que tarde en implementar las nuevas requests.

Se agradece cualquier Pull Request si tienes conocimiento en la materia :)

Si encuentras algún error, puedes abrir un Issue.

## To-Do

- [x] Sensor de último consumo disponible
- [x] Soportar múltiples contratos
- [x] Publicar el consumo en [Energía](https://www.home-assistant.io/docs/energy/)
- [x] Login automático con 2Captcha
- [x] Importar los costes de las facturas

## Agradecimientos

Este proyecto está basado en el excelente trabajo de [rndm2/hass-aigues-barcelona](https://github.com/rndm2/hass-aigues-barcelona), que a su vez es un fork de [duhow/hass-aigues-barcelona](https://github.com/duhow/hass-aigues-barcelona). Gracias a ambos por sentar las bases de esta integración.
