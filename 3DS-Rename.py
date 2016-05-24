##//////////////////-----Call libraries
import os
import csv
import sys
import binascii #pasar ninario a ascii
from Tkinter import * #interfaz grafica
from tkFileDialog import askdirectory  #pide carpeta
import tkMessageBox
import Tkinter as tk
import ttk
from xmlutils.xml2csv import xml2csv #xml parsher
import urllib2 #descarga archivos
import re #renombra
import sqlite3 # base de datos


##//////////////////-----Database
db = sqlite3.connect(':memory:') #crear tabla en memoria
db.text_factory = lambda x: unicode(x, "utf-8", "ignore") #indicar que el tipo de texto almacenado se codifica en utf-8
cursor = db.cursor()
cursor.execute('''
    CREATE TABLE datos(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, newname TEXT,
                       tid TEXT, crt TEXT)
''')

##//////////////////-----Funciones
def insertindb(fn,nn,ti,cr):
    cursor.execute('''INSERT INTO datos(filename, newname, tid, crt)
                  VALUES(?,?,?,?)''', (fn,nn,ti,cr))

def mostrar():
    tree.delete(*tree.get_children())
    cursor.execute('SELECT * from datos')
    data=cursor.fetchall()
    if len(data)==0:
        mostrarerror('No games found')
    else:
        for row in data:
            if "---" in row[2]:
                if row[0]%2:
                    tree.insert('', 'end', values=row[1:],tags = ('par_row','noindb'))
                else:
                    tree.insert('', 'end', values=row[1:],tags = ('noindb'))
            elif row[2] in row[1]:
                if row[0]%2:
                    tree.insert('', 'end', values=row[1:],tags = ('par_row','correctname'))
                else:
                    tree.insert('', 'end', values=row[1:],tags = ('correctname'))
            else:
                if row[0]%2:
                    tree.insert('', 'end', values=row[1:],tags = ('par_row',))
                else:
                    tree.insert('', 'end', values=row[1:])

def descargar():
    #descargar xml a csv
    try:
        archivoDescargar = "http://3dsdb.com/xml.php"
        inputs = urllib2.urlopen(archivoDescargar)
        output = "3dsdb.csv"
        converter = xml2csv(inputs, output, encoding="utf-8")
        converter.convert(tag="release",delimiter=";")

        #eliminar caracteres especiales y limpiar nombres
        original_string = open('3dsdb.csv').read()
        nuevo_string = re.sub('333;', 'o', original_string)
        nuevo_string = re.sub('&', 'and', nuevo_string)
        nuevo_string = re.sub(':', ' -', nuevo_string)
        nuevo_string = re.sub('"', '', nuevo_string)
        nuevo_string = re.sub('Rev[0-9][0-9]', '', nuevo_string)
        nuevo_string = re.sub('Rev[0-9]', '', nuevo_string)
        nuevo_string = re.sub(r'[\*|:<>?/#().]', '', nuevo_string)
        nuevo_string = re.sub('  ', ' ', nuevo_string)
        open('3dsdb.csv', 'w').write(nuevo_string)
        tkMessageBox.showinfo('Info', "The database has been successfully downloaded", icon='info')
    except:
        mostrarerror("Failed to download database")
        compdatabase()

def pidecarpeta(): #pedir carpeta
    global dirname
    dirname= askdirectory()
    recorrearchivos()

def recorrearchivos():
    cursor.execute('''DELETE FROM datos WHERE id > -1''') # eliminar datos de la base
    try:
        for file in os.listdir(dirname): #recorre los ficheros
            fpath = dirname+"/"+file
            # si es CIA
            if file.endswith((".cia",".CIA",".Cia",".CIa",".CiA",".cIa",".cIA",".ciA")):
                filename=file
                with open(fpath,"rb") as fcia: # abre el archivo en hexadecimal
                    fcia.seek(0x2C1C) # busca la posicion
                    title_id = binascii.hexlify(fcia.read(8)) # lee 8 digitos y los convierte en ascii
                    fcia.seek(0x3A90) # busca la posicion
                    ctrcia = binascii.hexlify(fcia.read(10)) # lee 10 digitos y los convierte en ascii
                    serial = ctrcia.decode("hex")
                fcia.close()
            #si es 3DS o 3DZ
            if file.endswith((".3ds",".3DS",".3Ds",".3dS",".3dz",".3DZ",".3Dz",".3dZ")):
                filename=file
                with open(fpath, "rb") as f3d: # abre el archivo en hexadecimal
                    f3d.seek(0x0108)  # busca la posicion
                    id_3d = f3d.read(8) # lee 8 digitos
                    title_id = binascii.hexlify(id_3d[::-1]) # los convierte en ascii y lo invierte
                    f3d.seek(0x1150) # busca la posicion
                    ctr3d = binascii.hexlify(f3d.read(10)) # lee 10 digitos y los convierte en ascii
                    serial = ctr3d.decode("hex")
                f3d.close()

            if "filename" in locals(): #si ha encontrado un cia o un 3ds...
            #comprobar patron
                if "00040" not in title_id.upper():
                    title_id="---"
                if "CTR" not in serial.upper():
                    serial="---"
                nnewname=buscatitulo(title_id.upper(),serial)
                if not nnewname:
                    nnewname="---"
                insertindb(filename,nnewname,title_id.upper(),serial.upper())
            #borrar variables
                del filename
                del nnewname
                del title_id
                del serial
        carpetaselect.set(dirname) # asignar carpeta para mostrar en la etiqueta
        mostrar()
    except Exception,e:
        print e
        tree.delete(*tree.get_children())
        carpetaselect.set("")
            
def buscatitulo(tid,ctr):
    try:
        with open("3dsdb.csv") as csvfile:
            sese="CTR-"+ctr[6:10]
            for line in csv.reader(csvfile, delimiter=';'): 
                if tid in line:
                    if not "found_title" in locals():
                        found_title=line
                    if sese.lower() in line:
                        found_title=line
            if "found_title" in locals():
                return found_title[1]+" ["+found_title[3]+"]"+" ["+found_title[0]+"]"
    except Exception,e:
        compdatabase()

def mostrarerror(errmsg): #funcion para mostrar ventana de errores
    tkMessageBox.showerror("Error",errmsg)

def renombrar():
    cursor.execute('SELECT filename,newname from datos where newname !="---"')
    for row in cursor.fetchall():
        old_nombre=dirname+"/"+row[0]
        extension=os.path.splitext(old_nombre)[1]
        nuevo_nombre=dirname+"/"+row[1]+extension
        if old_nombre != nuevo_nombre:
            count=2
            while os.path.isfile(nuevo_nombre):
                nuevo_nombre=dirname+"/"+row[1]+" ("+str(count)+")"+extension
                count+=1
            os.rename(old_nombre,nuevo_nombre)
    recorrearchivos()

def resource_path(relative_path): #obtener ruta de carpeta temporal
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def compdatabase(): #comprobar base de datos
	if not os.path.exists("3dsdb.csv"):
	    result = tkMessageBox.askquestion('Error', "The database was not found, Would you like to download it?", icon='error')
	    if result == 'yes':
	        descargar()
	    else:
	        sys.exit()

##//////////////////-----Interfaz grafica
v0 = Tk() # Tk() Es la ventana principal

v0.title("3DS Rename") #titulo
v0.iconbitmap(resource_path('3dsrename.ico')) #icono app
v0.config(bg="#009688") # Le da color al fondo
v0.geometry("650x400") # Cambia el tamanno de la ventana
v0.minsize(width=650, height=400) # tamanno minimo de la ventana

menu1 = Menu(v0)
v0.config(menu=menu1)
menu1_1 = Menu(menu1, tearoff=0)
menu1.add_cascade(label="Menu", menu=menu1_1)
menu1_1.add_command(label="Update database",command=lambda: descargar())
menu1_1.add_command(label="About",command=lambda: tkMessageBox.showinfo('About', "3DS Rename v3.0\nBy Medly13", icon='info'))

frame2=Frame(v0)
frame2.pack(padx=20,pady=10,fill = X)

l1=Label(frame2,text="Folder: ", anchor=W)
l1.config(bg="#009688",bd=0,fg="white")
l1.pack(side=LEFT)

carpetaselect=StringVar()
w=Label(frame2,textvar=carpetaselect, anchor=W)
w.config(bd=0)
w.pack(side=LEFT)

frame0=Frame(v0)
frame0.pack(expand=1,fill=BOTH,padx=20,pady=10)

tree = ttk.Treeview(frame0)

vsb = ttk.Scrollbar(frame0,orient="vertical", command=tree.yview)
vsb.pack(side=RIGHT,fill=BOTH)
hsb = ttk.Scrollbar(frame0,orient="horizontal", command=tree.xview)
hsb.pack(side=BOTTOM,fill=BOTH)

tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
tree["columns"]=('File', 'Newname', 'Title id', 'ctr')
tree['show'] = 'headings' # oculta la columna de identificador de tabla
tree['selectmode'] = 'none' # quita poder seleccionar

tree.heading("#1", text='File')
tree.column("#1", minwidth=190, width=190)
tree.heading("#2", text='Newname')
tree.column("#2", minwidth=190, width=190)
tree.heading("#3", text='Title id')
tree.column("#3", minwidth=110, width=110,stretch=False)
tree.heading("#4", text='Serial')
tree.column("#4", minwidth=100, width=100,stretch=False)

tree.tag_configure('par_row', background='#e0e9ef')
tree.tag_configure('correctname', foreground="#336600")
tree.tag_configure('noindb', foreground="#c80000")

tree.pack(expand=1,fill=BOTH)

frame1=Frame(v0,)
frame1.config(bg="#009688")
frame1.pack(padx=20,pady=10)

b2=Button(frame1,text="Select folder", height=2, width=32,compound="center",command=lambda: pidecarpeta())#boton pedir carpeta
b2.config(bg="#4c4a48",bd=0,fg="white",cursor="hand2")
b2.pack(side=LEFT,padx=20)

b3=Button(frame1,text="Rename", height=2, width=32,compound="center",command=lambda: renombrar())#boton renombrar
b3.config(bg="#4c4a48",bd=0,fg="white",cursor="hand2")
b3.pack(side=LEFT,padx=20)

compdatabase()
v0.mainloop()