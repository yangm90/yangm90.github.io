#!/usr/bin/python  
#coding utf8  
import  markdown  
import  sys  
sys.defaultencoding=('utf8')  
sys.defaultdecoding=('utf8')  
filename=sys.argv[1]  
markfile=open(filename)  
markcontent=markfile.read();  
print "markcontent type:", type(markcontent)#str ob  
htmlcontent=markdown.markdown(markcontent.decode('utf8'))#  
print "htmlcontent type:", type(htmlcontent)#unicode ob  
htmlfilename=filename+".html"  
htmlfile=open(htmlfilename, "w")  
htmlcontent=htmlcontent.encode('gbk')#translate into str  
htmlfile.write(htmlcontent)  
htmlfile.close()  
markfile.close()  
