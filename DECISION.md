# Decisão de arquitectura

## Escolha
Para o MVP do hospital, será usado um **orquestrador próprio pequeno**, e não uma tentativa de configurar o Hermes Agent inteiro como plataforma principal.

## Motivo
A configuração do Hermes não produziu uma experiência suficientemente previsível para o caso do hospital. O núcleo próprio permite controlar diretamente estados, permissões, aprovação humana, auditoria e ferramentas. Hermes, Ollama, vLLM e outros endpoints podem ser integrados depois através do adaptador de modelo.

## Consequência
O MVP não pretende replicar todas as capacidades do Manus imediatamente. Ele estabelece uma fundação testável: planear, executar skills limitadas, validar, solicitar aprovação e auditar. A complexidade só será acrescentada quando uma necessidade concreta for validada.
