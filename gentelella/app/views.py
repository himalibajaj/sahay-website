from django.shortcuts import render
from django.template import loader
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import csv
import re
import redis
import os
import os
import google.generativeai as genai
from datetime import datetime, timedelta


GOOGLE_API_KEY='AIzaSyBBxGZJriCR4aPgvlkddEdYygAY4BOauqI'
genai.configure(api_key=GOOGLE_API_KEY)

for m in genai.list_models():
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)

model = genai.GenerativeModel('gemini-flash-latest')
chat = model.start_chat(history=[])
#while True:
#    prompt = input("Ask me anything: ")
#    if (prompt == "exit"):
#        break
#    response = chat.send_message(prompt, stream=True)
#    for chunk in response:
#        if chunk.text:
#          print(chunk.text)



POOL = redis.ConnectionPool(host='127.0.0.1', decode_responses=True, port=6379, db=0)

# For production: use Redis URL from environment variable
if os.environ.get('REDIS_URL'):
    datastore = redis.Redis.from_url(os.environ.get('REDIS_URL'), decode_responses=True)
else:
    datastore = redis.StrictRedis(connection_pool=POOL)

replace = lambda x: x.replace(u'\xa0', u' ')
trimstr = lambda x: x.strip()
statename=""
pincodealllist=[]
directory_path="/cdot/docs/"
with open('court_address2.csv', mode ='r', encoding='utf-8')as file:
  csvFile = csv.reader(file,delimiter ="#")
  for lines in csvFile:
        res0 = list(map(replace, lines))
        res = list(map(trimstr, res0))
        if len(res) == 1 :
           statename=res[0]
           continue
        if len(res) == 4 :
           if statename == "":
              continue
           statename=statename.replace('\"','')
           slno=res[0]
           court_name=res[1]
           addr=res[2]
           phoneno=res[3]
           pt=re.compile(r'\b(?!0)\d{6}\b')
           pincodelist=pt.findall(addr)
           if len(pincodelist) == 0 : 
              pincodelist=['']  
           pincode= pincodelist[0].strip()
           #print(statename,"  ",addr,"   ",pincode)
           court_dict={}
           court_dict["slno"]=slno
           court_dict["court_name"]=court_name
           court_dict["addr"]=addr
           court_dict["phoneno"]=phoneno
           court_dict["pincode"]=pincode
           datastore.hmset("statename:slno:"+statename+":"+slno, court_dict)  
           datastore.sadd("statewiselist:"+statename, slno) 
           datastore.sadd("statelist", statename)
           datastore.sadd("pincodelist", pincode)
           datastore.hmset("pincode:"+pincode, court_dict)
           datastore.set("pincode:state:"+pincode, statename)
           if pincode.isdigit() :
              pincodealllist.append(pincode)


@csrf_exempt 
def get_con():
   POOL2 = redis.ConnectionPool(host='192.168.186.102', decode_responses=True, port=6379, db=0)
   datastore2 = redis.StrictRedis(connection_pool=POOL)
   return datastore2

           
@csrf_exempt              
def load_directory_content(directory_path):
    """Loads text content from all files in the given directory."""
    text_content = ""
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        if os.path.isfile(file_path) and filename.endswith(".txt"):
            with open(file_path, 'r') as file:
                text_content += file.read() + "\n"
    return text_content
    
    
 
def index(request):
    context = {}
    template = loader.get_template('app/index.html')
    return HttpResponse(template.render(context, request))

@csrf_exempt 
def gentella_html(request):
    context = {}
    # The template to be loaded as per gentelella.
    # All resource paths for gentelella end in .html.

    # Pick out the html file name from the url. And load that template.
    load_template = request.path.split('/')[-1]
    template = loader.get_template('app/' + load_template)
    return HttpResponse(template.render(context, request))


@csrf_exempt      
def courtdetails(request):
    statename=request.POST.get('statename')
    print("statename=",statename)
    context = {}
    statelist = datastore.smembers('statelist')
    statelist2=list(statelist)
    if statename == None:
       statename=statelist2[0]
    if statename == '':
       statename=statelist2[0]
    response_data = {}
    response_data['court_count']=0
    cnt=0
    response_data['courtlist']=[]
    for slno in datastore.smembers("statewiselist:"+statename):
        courtdict = {} 
        courtdict = datastore.hgetall("statename:slno:"+statename+":"+slno);
        courtdict["slno"]=cnt+1 
        response_data['courtlist'].append(courtdict)
        cnt = cnt + 1
        response_data['court_count']=cnt
    load_template = request.path.split('/')[-1]
    print(load_template)
    print(statelist)
    template = loader.get_template('app/' + load_template)
    context = {    'receivedJsonString': response_data,
                   'curstatename': statename ,
                   'statelist':  statelist ,
               }
    return HttpResponse(template.render(context, request))
    
    
    
@csrf_exempt      
def reports(request):
    pinnumber=request.POST.get('number')
    companyname=request.POST.get('companyname')
    grievancedetails=request.POST.get('grievancedetails')
    myname=request.POST.get('name')
    myemail=request.POST.get('email')
    
    print("pinnumber=",pinnumber)
    statelist = datastore.smembers('statelist')
    context = {}
    maxmatch=-1
    nearestpin=pinnumber
    for pinitr in pincodealllist: 
        lcp=os.path.commonprefix([pinnumber,pinitr])
        if len(lcp)> maxmatch : 
           maxmatch = len(lcp)
           nearestpin=pinitr
        if len(lcp) == len(pinitr) :
            nearestpin=pinitr
            break
    courtdict = {}       
    courtdict = datastore.hgetall("pincode:"+nearestpin);    
    cnt=0
    response_data = {}
    response_data['nearest_court_count']=0
    response_data['nearestcourtlist']=[]
    response_data['nearestcourtlist'].append(courtdict)
    cnt = cnt + 1
    response_data['nearest_court_count']=cnt
    statename =datastore.get("pincode:state:"+nearestpin)
    cnt=0
    response_data2 = {}
    response_data2['nearest_court_count']=0
    response_data2['courtlist']=[]
    for slno in datastore.smembers("statewiselist:"+statename):
        courtdict = {} 
        courtdict = datastore.hgetall("statename:slno:"+statename+":"+slno);
        courtdict["slno"]=cnt+1 
        response_data2['courtlist'].append(courtdict)
        cnt = cnt + 1
        response_data2['court_count']=cnt
    prompt = "What is the website of "+companyname+"?"
    print(prompt)
    companywebsite=""
    companywebsiter = chat.send_message(prompt, stream=True)
    for chunk in companywebsiter:
        if chunk.text:
          companywebsite=companywebsite+ " "+chunk.text
          
    prompt = "Tell me some details within 50 words about the company named "+companyname+"."
    print(prompt)
    companydetails=""
    companydetailsr = chat.send_message(prompt, stream=True)
    for chunk in companydetailsr:
        if chunk.text:
          companydetails=companydetails+ " "+chunk.text
          
    prompt = "Write 1 tweet for a grievance within 60 words against comapany named"+companyname+" where grievance details is "+grievancedetails +". Add proper receipient and hashtag for that tweet."+ "My name is "+myname +" and my email id is "+myemail +" and my pincode is "+pinnumber
    print(prompt)
    grievancetweet=""
    grievancetweetr = chat.send_message(prompt, stream=True)
    for chunk in grievancetweetr:
        if chunk.text:
          grievancetweet=grievancetweet+ " "+chunk.text
          
    prompt = "Write 1 sample formatted mail for a grievance within 50 words against comapany named"+companyname+" where grievance details is "+grievancedetails +". Add proper receipient in the mail."+ "My name is "+myname +" and my email id is "+myemail
    print(prompt)
    grievancemail=""
    grievancemailr = chat.send_message(prompt, stream=True)
    for chunk in grievancemailr:
        if chunk.text:
          grievancemail=grievancemail+ " "+chunk.text
          
          
    prompt = "Answer the follwing question within 50 words.What is closest consumer court address and contact details for pincode "+pinnumber
    print(prompt)
    ccc=""
    cccr = chat.send_message(prompt, stream=True)
    for chunk in cccr:
        if chunk.text:
          ccc=ccc+ " "+chunk.text
          
    
          
          
    load_template = request.path.split('/')[-1]
    print(load_template)
    template = loader.get_template('app/' + load_template)
    context = {    'receivedJsonString': response_data,
                   'receivedJsonString2': response_data2,
                   'curstatename': statename ,
                   'statelist':  statelist ,
                   'companywebsite': companywebsite ,
                   'companydetails': companydetails,
                   'grievancetweet': grievancetweet,
                   'grievancemail': grievancemail,
                   'ccc': ccc,
               }
    return HttpResponse(template.render(context, request))
    



     
@csrf_exempt  
def ask_question(directory_path, question):
    """Answers a question based on the content of the directory."""
    context=""
    try:
       context = load_directory_content(directory_path)
    except:
       context=""
    prompt = f"Answer the following question within 30 words  based on the provided context:\n\nContext:\n{context}\n\nQuestion: {question}"
    if context == '':
       prompt = f"Generate answer within 30 words  \n\tText: {question}"
    response = model.generate_content(prompt)
    return response.text  




@csrf_exempt      
def get_chat_response_ajax(request):
    input=request.POST['input']  
    print(input)
    output=ask_question(directory_path, input)
    response_data = {}
    response_data['output'] = output
    return JsonResponse(response_data, status=200) 
    















@csrf_exempt      
def year_2025(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2025")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2025"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2024(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2024")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2024"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2023(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2023")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2023"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2022(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2022")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2022"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2021(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2021")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2021"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2020(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2020")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2020"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2022(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2022")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2022"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2019(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2019")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2019"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2018(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2018")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2018"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2017(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2017")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2017"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        




@csrf_exempt      
def year_2016(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2016")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2016"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           







@csrf_exempt      
def year_2015(request):
    #statename=request.POST.get('statename')
    #print("statename=",statename)
    datastore2 = get_con()
    print("year_2015")
    context = {}
    all_case_type=[]
    all_case_type_count=[]
    delayed_case_type_count=[]
    total_case=0
    total_hearing=0
    total_pending=0
    total_completed=0
    total_case_type=0
    average_completion_time=0
    total_number_hearing_count = [0] * 100
    top1_days_case_length=0
    top2_days_case_length=0
    top3_days_case_length=0
    top4_days_case_length=0
    for case_number in datastore2.smembers('all_case_set'):
        print("\ncurrent case_number="+case_number)
        if case_number.endswith("2015"):
           total_case = total_case + 1
           case_type = case_number.split("/")[1]
           ct_index=0
           total_number_hearing=0
           total_number_hearing=datastore2.scard('all_case_wise_hearing_set:'+case_number)
           total_number_hearing_count[total_number_hearing]=total_number_hearing_count[total_number_hearing]+1
           filing_date=datastore2.hget( "case_details_hm:"+case_number, "filing_date_element")
           case_stage=datastore2.hget( "case_details_hm:"+case_number, "case_stage_element")
           next_hearing_element=datastore2.hget( "case_details_hm:"+case_number, "next_hearing_element")
           date_format = "%d-%m-%Y"
           print("(",case_stage,")")
           if case_stage != "\"DISPOSED OFF\"" and case_stage != "\"DISMISSED\"":
              total_pending = total_pending + 1
           else:
              total_completed = total_completed + 1
              
           if filing_date is not None  :
              filing_date = filing_date[1:]
              filing_date = filing_date[:-1]
              if len(filing_date) != 10:
                 continue
              filing_date_object = datetime.strptime(filing_date, date_format)
              
              for hearing_date in datastore2.smembers('all_case_wise_hearing_set:'+case_number):
                  total_hearing = total_hearing + 1
                  hearing_date_object = datetime.strptime(hearing_date, date_format)
                  date_gap= hearing_date_object - filing_date_object
                  current_hearing_date=datastore2.hget( "all_case_wise_hearing_details_hm:"+case_number+":"+hearing_date,"date_of_hearing")
                  if case_stage == "\"DISPOSED OFF\"" or case_stage == "\"DISMISSED\"":
                       average_completion_time =average_completion_time + date_gap.days
                  if top1_days_case_length < date_gap.days:
                     top1_days_case_length=date_gap.days
                  if top2_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length:
                     top2_days_case_length=date_gap.days
                  if top3_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length:
                     top3_days_case_length=date_gap.days
                  if top4_days_case_length < date_gap.days  and date_gap.days < top1_days_case_length  and date_gap.days < top2_days_case_length and date_gap.days < top3_days_case_length:
                     top4_days_case_length=date_gap.days
                   
           for cti in all_case_type:
                if cti == case_type:
                   break;
                ct_index = ct_index + 1
           if ct_index == len(all_case_type):
              all_case_type.append(case_type)
              all_case_type_count.append("0")
              delayed_case_type_count.append("0")
           all_case_type_count[ct_index]=( (str)((int)(all_case_type_count[ct_index])+1))
           if ((int) (all_case_type_count[ct_index])) > 2:
              delayed_case_type_count[ct_index]=( (str)((int)(delayed_case_type_count[ct_index])+1))
           print("\ntotal_case=",total_case)
     
    total_number_hearing_count_tmp = total_number_hearing_count[:] 
    ct_index=0
    for ct in all_case_type:
        if ct == "MA":
           all_case_type[ct_index]="Mutual Agreement"
           
        if ct == "IA":
           all_case_type[ct_index]="Interim Application"
           
        if ct == "SA":
           all_case_type[ct_index]="Section Appeal"
           
        if ct == "FA":
           all_case_type[ct_index]="Final Appeal"
           
        if ct == "RA":
           all_case_type[ct_index]="Review Application"
         
        if ct == "RP":
           all_case_type[ct_index]="Revision Petition"
         
        if ct == "EA":
           all_case_type[ct_index]="Execution Application"
           
        if ct == "CC":
           all_case_type[ct_index]="Complaint Case"
           
        ct_index = ct_index +1
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = mi
    top1_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = mi
    top2_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = mi
    top3_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = mi
    top4_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    m=0
    i=0
    mi=0
    for itr in total_number_hearing_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = mi
    top5_case_hearing_count = m
    total_number_hearing_count_tmp[mi]="0"
    
    total_number_hearing_days_tmp2=[top1_case_hearing_days,top2_case_hearing_days,top3_case_hearing_days,top4_case_hearing_days,top5_case_hearing_days]  
    total_number_hearing_count_tmp2=[top1_case_hearing_count,top2_case_hearing_count,top3_case_hearing_count,top4_case_hearing_count,top5_case_hearing_count]  
       
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_hearing_days = m
    top1_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_hearing_days = m
    top2_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_hearing_days = m
    top3_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_hearing_days = m
    top4_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    m=10000
    i=0
    mi=0
    for itr in total_number_hearing_days_tmp2:
        if (int)(itr) < m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_hearing_days = m
    top5_case_hearing_count = total_number_hearing_count_tmp2[mi]
    total_number_hearing_days_tmp2[mi]="10000"
    
    
    
    
    
    
    
    
           
    delayed_case_type_count_tmp = delayed_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_dealyed_case_type = all_case_type[mi]
    top1_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_dealyed_case_type = all_case_type[mi]
    top2_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_dealyed_case_type = all_case_type[mi]
    top3_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"       
    
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_dealyed_case_type = all_case_type[mi]
    top4_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0"
 
 
     
    m=0
    i=0
    mi=0
    for itr in delayed_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_dealyed_case_type = all_case_type[mi]
    top5_dealyed_case_type_count = m
    delayed_case_type_count_tmp[mi]="0" 
    
           
    all_case_type_count_tmp = all_case_type_count[:]
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top1_case_type = all_case_type[mi]
    top1_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top2_case_type = all_case_type[mi]
    top2_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top3_case_type = all_case_type[mi]
    top3_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top4_case_type = all_case_type[mi]
    top4_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    
    m=0
    i=0
    mi=0
    for itr in all_case_type_count_tmp:
        if (int)(itr) > m:
            m= (int)(itr)
            mi=i
        i=i+1
    top5_case_type = all_case_type[mi]
    top5_case_type_count = m
    all_case_type_count_tmp[mi]="0"
    
    x1=top1_case_type_count
    x2=top2_case_type_count
    x3=top3_case_type_count
    x4=top4_case_type_count
    x5=top5_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    
    
    
    x1=top1_dealyed_case_type_count
    x2=top2_dealyed_case_type_count
    x3=top3_dealyed_case_type_count
    x4=top4_dealyed_case_type_count
    x5=top5_dealyed_case_type_count
    if x1 <= 0:
       x1=1
    if x2 <= 0:
       x2=1
    if x3 <= 0:
       x3=1
    if x4 <= 0:
       x4=1
    if x5 <= 0:
       x5=1
    top1_dealyed_case_type_count=round((x1/(x1+x2+x3+x4+x5))*100,2)
    top2_dealyed_case_type_count=round((x2/(x1+x2+x3+x4+x5))*100,2)
    top3_dealyed_case_type_count=round((x3/(x1+x2+x3+x4+x5))*100,2)
    top4_dealyed_case_type_count=round((x4/(x1+x2+x3+x4+x5))*100,2)
    top5_dealyed_case_type_count=round((x5/(x1+x2+x3+x4+x5))*100,2)
    total_case_type = len(all_case_type)   
    print("all_case_type",all_case_type,"all_case_type_count",all_case_type_count)
    load_template = request.path.split('/')[-1]
    print(load_template)
    if average_completion_time != 0 and total_completed != 0: 
       average_completion_time=(int) (round(average_completion_time/ total_completed,0))
    
    if total_case != 0 : 
       completion_rate=(int) (round(total_completed/ total_case,0))
       
          
    template = loader.get_template('app/' + load_template)
    print("top1_case_hearing_days=",top1_case_hearing_days)
    print("top2_case_hearing_days=",top2_case_hearing_days)
    print("top3_case_hearing_days=",top3_case_hearing_days)
    print("top4_case_hearing_days=",top4_case_hearing_days)
    print("top5_case_hearing_days=",top5_case_hearing_days)
    print("top1_case_hearing_count=",top1_case_hearing_count)
    print("top2_case_hearing_count=",top2_case_hearing_count)
    print("top3_case_hearing_count=",top3_case_hearing_count)
    print("top4_case_hearing_count=",top4_case_hearing_count)
    print("top5_case_hearing_count=",top5_case_hearing_count)
    context = {    
                   'total_case': total_case ,
                   'total_hearing': total_hearing,
                   'total_pending': total_pending,
                   'total_completed': total_completed,
                   'top1_case_type': top1_case_type ,
                   'top2_case_type': top2_case_type ,
                   'top3_case_type': top3_case_type ,
                   'top4_case_type': top4_case_type ,
                   'top5_case_type': top5_case_type ,
                   'total_case_type': total_case_type,
                   'top1_case_type_countp': top1_case_type_count ,
                   'top2_case_type_countp': top2_case_type_count ,
                   'top3_case_type_countp': top3_case_type_count ,
                   'top4_case_type_countp': top4_case_type_count ,
                   'top5_case_type_countp': top5_case_type_count ,
                   'top1_case_type_count': x1 ,
                   'top2_case_type_count': x2 ,
                   'top3_case_type_count': x3 ,
                   'top4_case_type_count': x4 ,
                   'top5_case_type_count': x5 ,
                   'top1_case_hearing_days': top1_case_hearing_days,
                   'top2_case_hearing_days': top2_case_hearing_days,
                   'top3_case_hearing_days': top3_case_hearing_days,
                   'top4_case_hearing_days': top4_case_hearing_days,
                   'top5_case_hearing_days': top5_case_hearing_days,
                   'top1_case_hearing_count': top1_case_hearing_count,
                   'top2_case_hearing_count': top2_case_hearing_count,
                   'top3_case_hearing_count': top3_case_hearing_count,
                   'top4_case_hearing_count': top4_case_hearing_count,
                   'top5_case_hearing_count': top5_case_hearing_count,
                   'top1_days_case_length': top1_days_case_length,
                   'top2_days_case_length': top2_days_case_length,
                   'top3_days_case_length': top3_days_case_length,
                   'top4_days_case_length': top4_days_case_length,
                   'top1_dealyed_case_type': top1_dealyed_case_type,
                   'top2_dealyed_case_type': top2_dealyed_case_type,
                   'top3_dealyed_case_type': top3_dealyed_case_type,
                   'top4_dealyed_case_type': top4_dealyed_case_type,
                   'top5_dealyed_case_type': top5_dealyed_case_type,
                   'top1_dealyed_case_type_count': top1_dealyed_case_type_count,
                   'top2_dealyed_case_type_count': top2_dealyed_case_type_count,
                   'top3_dealyed_case_type_count': top3_dealyed_case_type_count,
                   'top4_dealyed_case_type_count': top4_dealyed_case_type_count,
                   'top5_dealyed_case_type_count': top5_dealyed_case_type_count,
                   'average_completion_time': average_completion_time,
                   'completion_rate': completion_rate,
                   

               }
    datastore2.close()
    return HttpResponse(template.render(context, request))           



        
        

