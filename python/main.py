import shutil
import os.path
import random
import sys
import time
import asyncio
from ftplib import FTP
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from configparser import ConfigParser
import ftplib
import pidfile

# GLOBAL VARIABLES
#check config.ini for details                                                   IMPLEMENT EXIT() AND DELETE/MOVE FILES
videosPath = ""
movePath = ""
quanttotal = 0      #to be removed
limitNoChangeTime=0
hora_inicio = datetime.now()  
quant = 0    #amount of finished uploads                       
global_percentComplete = '0';

# LOAD CONFIG FILE

def Setup():

    global videosPath, movePath, limitNoChangeTime


    config = ConfigParser()
    config.read("config.ini")

    try:
        config_data = config['default']
        print ("Config file loaded. FTP:",config_data['ftp_host'] )
    except Exception as err:
        print (err)
        print(bcolors.FAIL +"Something went wrong while loading config file!"+bcolors.ENDC)
        os.remove("./ytdlpToFTP.pid")
        os._exit(1);
        
    
    videosPath = config_data['files_dir']   
    movePath = config_data['files_move_dir']
    limitNoChangeTime = int(config_data['limitNoChangeTime']) 

         # Ftp login and setup

    try: # make it  a function and call on main
        ftp = ftplib.FTP()

        ftp.connect(config_data['ftp_host'], int(config_data['ftp_port'])) #port has to be int, idk why
        print (bcolors.HEADER, ftp.getwelcome(), bcolors.ENDC)
        try:
            print ("Logging in...")

            ftp.login(config_data['ftp_username'], config_data['ftp_password'])
            ftp.cwd(config_data['ftp_path'])
            print (bcolors.OKGREEN+"Logged-in."+bcolors.ENDC)

        except Exception as err:
            print (err)
            print(bcolors.FAIL +"Credencials Error!"+bcolors.ENDC)
            os.remove("./ytdlpToFTP.pid")
            os._exit(1); 
    except Exception as err:
        print (err)
        print(bcolors.FAIL +"Failed to reach the FTP server"+bcolors.ENDC)
        
        os.remove("./ytdlpToFTP.pid") #funtion to dedicated to stop program is really needed
        os._exit(1);       
        
    return(ftp)


#PROGRESS PERCENTAGE
class FtpUploadTracker:
    
    sizeWritten = 0
    totalSize = 0
    lastShownPercent = 0
    percentComplete = 0
    def __init__(self, totalSize):
        self.totalSize = totalSize
    
    def handle(self, block):
        global global_percentComplete
        self.sizeWritten += 1024
        percentComplete = round((float(self.sizeWritten) / float(self.totalSize)) * 100)
        global_percentComplete = str(percentComplete)
        if (self.lastShownPercent != percentComplete):
            self.lastShownPercent = percentComplete
           
                                                     
            sys.stdout.write("  " + str(percentComplete) + "% uploaded... \r")
            sys.stdout.flush()


# CHECK IF UPLOAD HAS FREEZED
async def check_freeze():
     
  while True:
        old_percentComplete = global_percentComplete
        #print ("           OLD_PERCENTAGE ", old_percentComplete)
        await asyncio.sleep (5); #checking frequency

        hora_atual = datetime.now()  
        time_difference = hora_atual - hora_inicio                              
        time_difference_in_seconds = time_difference / timedelta(seconds=1)
        
        #print ("           NEW_PERCENTAGE ", global_percentComplete)
        if (old_percentComplete == global_percentComplete) and (time_difference_in_seconds > limitNoChangeTime):
            await asyncio.sleep (10);
            if (old_percentComplete == global_percentComplete):    
                print (bcolors.FAIL + "  Taking too long: ",time_difference_in_seconds, " - ", old_percentComplete, " = " ,global_percentComplete, bcolors.ENDC); 
                os.remove("./ytdlpToFTP.pid")
                os.execv(sys.executable, ['python3'] + sys.argv) #restarts script
                
        
        #else:
            #print (bcolors.OKGREEN + " TIME IS OK:", time_difference_in_seconds, bcolors.ENDC)
            

# FILE OPERATIONS AND UPLOAD    
async def upload_files():
    ftp = Setup();
    global quant
    global quanttotal
    global hora_inicio

    for file in os.listdir(videosPath):
            if file.endswith(".json") or file.endswith(".mkv") or file.endswith(".mp4") or file.endswith(".webm"):
               #print (bcolors.WARNING + "file added to counting" + bcolors.ENDC)
               quanttotal = quanttotal + 1;

    print(bcolors.OKCYAN + "[INFO]", quanttotal, " files were queued."+ bcolors.ENDC)

    for file in os.listdir(videosPath): 
     if file.endswith(".json") or file.endswith(".mkv") or file.endswith(".mp4") or file.endswith(".webm"):       
          try:
              
              
              hora_inicio = datetime.now()                                #marcando o tempo
            

              file_path = os.path.join(videosPath, file)      
              fileftp = open(file_path, 'rb')
              totalSize = os.path.getsize(file_path)               #file size
              print ("Started uploading: ",file," ...(", quant,"/", quanttotal,")", bcolors.OKCYAN, format_bytes(totalSize), bcolors.ENDC ) #printing file information 
              
              

              uploadTracker = FtpUploadTracker(int(totalSize))
              await asyncio.get_event_loop().run_in_executor(None, ftp.storbinary, f'STOR {file}', fileftp, 1024, uploadTracker.handle) 


              quant =  quant+1

              print (bcolors.OKCYAN,hora_inicio," -    <==[OK]==>   Finished uploading!" + bcolors.ENDC);

              #shutil.move( file_path,  movePath)          
              os.remove(file_path)  

          except Exception as err:
              print (err)
              print (bcolors.FAIL + 'An ERROR has occured during the upload!' + bcolors.ENDC)
              continue


     
 
          if  quant == (quanttotal):
            print (bcolors.WARNING +"[ALERT] Queue has ended, exiting program..."+bcolors.ENDC)
            os.remove("./ytdlpToFTP.pid")
            os._exit(1); 
            
async def main():

# CHECKS IF ANOTHER INSTANCE IS ALREADY RUNNING
 try:
    with pidfile.PIDFile("./ytdlpToFTP.pid"): #generated in current directory

     #run upload and freeze checker together   
     batch = asyncio.gather(upload_files(), check_freeze()) 
     result_upload, result_freeze = await batch     
        
 except pidfile.AlreadyRunningError:
    print('Already running.') 
    os._exit(1); 

# COLORED TEXT    
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# CORRECT SIZE FROM BYTES
def format_bytes(size):

    
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : "", 1: " kilo", 2: " mega", 3: " giga", 4: " tera"}
    while size > power:
        size /= power
        n += 1
    output = str(str.format("{0:.2f}", size) + str(power_labels[n])+ "bytes")
    output.replace("'","")
    return (output)


if __name__ == "__main__":
    asyncio.run(main());

sys.exit() 
