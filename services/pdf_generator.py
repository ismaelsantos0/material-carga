from reportlab.pdfgen import canvas
import os

def gerar_cautela_pdf(patrimonio, descricao, nome_militar, posto):
    caminho_arquivo = f"cautela_{patrimonio}.pdf"
    
    c = canvas.Canvas(caminho_arquivo)
    c.drawString(100, 800, "TERMO DE CAUTELA DE MATERIAL")
    c.drawString(100, 750, f"Material: {descricao} (Patrimônio: {patrimonio})")
    c.drawString(100, 700, f"Recebedor: {posto} {nome_militar}")
    c.drawString(100, 650, "Assumo a responsabilidade pelo equipamento acima.")
    
    c.drawString(100, 500, "___________________________________________________")
    c.drawString(150, 480, f"Assinatura - {posto} {nome_militar}")
    
    c.save()
    return caminho_arquivo
