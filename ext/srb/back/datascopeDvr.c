/*
 * datascopeDvr.c - Routines to handle  datascope database storage
 */

/*******/
#define DATASCOPEDEBUGON 1
/****/

#ifdef DATASCOPEDEBUGON 
#define DATASCOPE_DEBUG( ... ) fprintf( stdout, __VA_ARGS__ ); fflush( stdout );
#else
#define DATASCOPE_DEBUG( ... ) 
#endif

#include "datascopeSrbTools.h"
#include "datascopeMDriver.h"
#include <errno.h>
extern int errno;

int
makeDbgetvCall (Dbptr *datascopedbPtr, char *tableName,
		int numArgs, char *argv[], Dbvalue dbValueArr[])
{
 
    int i,j,k;

    for (i = 0; i < numArgs ; i++) {
	j =  dbgetv(*datascopedbPtr,tableName, argv[i], &dbValueArr[i], 0);
	if (j < 0)
	    return(j);
    }
    return(j);
}
/* datascopeOpen - Handles the open call.
 *
 * Input : MDriverDesc *mdDesc - The datascope descriptor handle
 *         char *datascopePathDesc - The datascope path name to be opened
 *         int datascopeFlags - The open flag
 *         int datascopeMode - The datascope mode
 *
 * Output : Returns the datascope descriptor of the opened datascope.
 */
int
datascopeOpen(MDriverDesc *mdDesc, char *rsrcInfo,
         char *datascopePathDescIn, int datascopeFlags, int datascopeInMode, char *userName)
{

  datascopeStateInfo *datascopeSI;
  char datascopeMode[4];
  char *tmpPtr;
  int i;
  Dbptr *datascopedb;
  Hook *hook = 0;

  Dbptr   dbtemp;
  Tbl     *tablenames;
  Tbl     *table_fieldnames;
  Tbl     *request_fieldnames;
  char    *tablename;
  char *datascopePathDesc;
  char    fieldname[STRSZ];
  int     is_view;
  int nrec;
  int     itable;
  int     ifield;
  char fileName[FILENAME_MAX];
  char fileName2[FILENAME_MAX];

  if((datascopeSI =  malloc(sizeof (datascopeStateInfo))) == NULL) {
    fprintf(stdout, "datascopeOpen:  Malloc error");
    return MEMORY_ALLOCATION_ERROR;
  }
 if((datascopedb =  malloc(sizeof (Dbptr))) == NULL) {
    fprintf(stdout, "datascopeOpen:  Malloc error");
    return MEMORY_ALLOCATION_ERROR;
  }
 datascopePathDesc = datascopePathDescIn;
 while (*datascopePathDesc == ' ')
     datascopePathDesc++;
 if ((tmpPtr = strstr(datascopePathDesc,"?SHADOW")) != NULL) 
     *tmpPtr = '\0';

 datascopeSI->dbPtrPtr = datascopedb;
 mdDesc->driverSpecificInfo = (char *) datascopeSI;
 if (strlen(datascopePathDesc) == 0)
     return(MDAS_SUCCESS);
 DATASCOPE_DEBUG("datascopeOpen: Start datascopeopen: datascopePathDesc=%s; datascopeMode=%s.\n",datascopePathDesc,datascopeMode);

  if (datascopeFlags == 0)
      strcpy(datascopeMode,"r");
  else
      strcpy(datascopeMode,"r+");
  unuralize(datascopePathDesc);
  unuralize(datascopePathDesc);
  if ((i = getDatascopeStateInfo( datascopeSI, rsrcInfo, datascopePathDesc, datascopeFlags, 
			datascopeInMode, userName)) <0 ) {
    fprintf(stdout, "datascopeOpen:  getStateInfo error:%i",i);
    freeDatascopeStateInfo(datascopeSI);
    free(datascopedb);
    return i;
  }
 
  datascopeSI->dbfilefd= NULL;
  datascopeSI->exprArray = NULL;
  DATASCOPE_DEBUG("datascopeOpen: Opening database\n");

  i = dbopen_database(datascopePathDesc, datascopeMode, datascopedb);
  if (i < 0) {
      fprintf(stdout, "datascopeOpen: datascopeopen error. datascopePathDesc=%s. errorCode=%d",
	      datascopePathDesc, i);fflush(stdout);
      free(datascopedb);
      
      return(MD_CONNECT_ERROR);
  }
  if (datascopeSI->dstable != NULL) {
    DATASCOPE_DEBUG("datascopeOpen: Start  dstable =%s\n",datascopeSI->dstable);
    if ((i = dbopen_table ( datascopeSI->dstable, datascopeMode, datascopedb )) < 0 ) {
      fprintf(stdout, "datascopeOpen: dstable error. %s %i",datascopeSI->dstable,i);
      freeDatascopeStateInfo(datascopeSI);fflush(stdout);
      return(MD_SET_ERROR);
    }
  }
  datascopeSI->dbPtrPtr = datascopedb;
  if (datascopeSI->dsfind != NULL || datascopeSI->dsfindRev != NULL ) {
    if (datascopeSI->dsfind != NULL) {
        DATASCOPE_DEBUG("datascopeOpen: Start  dsfind =%s\n",datascopeSI->dsfind);
	datascopedb->record =-1;
	i = dbfind (*datascopedb, datascopeSI->dsfind, 0 , &hook );
    }
    else {
        DATASCOPE_DEBUG("datascopeOpen: Start  dsfindRev =%s\n",datascopeSI->dsfindRev);
	i = dbquery( *datascopedb, dbRECORD_COUNT, &nrec );
	if (i < 0) {
	    fprintf(stdout, "datascopeOpen: dbquery1 for nrec Error: %i\n",i);
	    freeDatascopeStateInfo(datascopeSI);
	    return(i);
	}
        DATASCOPE_DEBUG("datascopeOpen: Start  dsfindRev Nrec =%i\n",nrec);

	datascopedb->record = nrec;
	i = dbfind (*datascopedb, datascopeSI->dsfindRev, 1, &hook );
    }
    if (i  < 0 ) {
      fprintf(stdout, "datascopeOpen: dsfind error. %s %i",datascopeSI->dsfind,i);
      freeDatascopeStateInfo(datascopeSI);
      DATASCOPE_DEBUG("datascopeOpen: After dsfind: FAILED: status=%i.\n",i);

      if (i == -1) 
	return(DATASCOPE_COMPILATION_ERROR);
      else if (i == -2) 
	return(DATASCOPE_END_OF_DATA_FOUND);
      else if (i == -3) 
	return(DATASCOPE_BEGIN_OF_DATA_FOUND);
      else
	return(MD_SET_ERROR);
    }
    datascopedb->record = i;
    
    DATASCOPE_DEBUG("datascopeOpen: Start  dsfindStatus =%i.\n",i);
  }

  if (datascopeSI->dsprocessStmt  != NULL) {
    DATASCOPE_DEBUG("datascopeOpen: Start  dbprocessStmt.\n");
    *datascopedb = dbprocess(*datascopedb, datascopeSI->dsprocessStmt, dbinvalid);
    if (datascopedb->database < 0) {
       i = datascopedb->database;
       fprintf(stdout, "datascopeOpen: dsprocess error. %i",i);fflush(stdout);
       freeDatascopeStateInfo(datascopeSI);
       DATASCOPE_DEBUG("datascopeOpen: After  dbprocessStmt: FAILED:  status=%i.\n",i);
       return(i);
    } 
    DATASCOPE_DEBUG("datascopeOpen: After  dbprocessStmt: datascopedb->database = %i.\n",datascopedb->database);
  }
  


  if (datascopeSI->dsprocessStmt  != NULL || datascopeSI->dsfind != NULL) {
    i = dbquery( *datascopedb, dbTABLE_IS_VIEW, &is_view );
    if (i < 0) {
      fprintf(stdout, "datascopeOpen: dbquery1 Error: %i\n",i);
      freeDatascopeStateInfo(datascopeSI);
      return(i);
    }	   
    if( is_view ) {
      i =dbquery( *datascopedb, dbVIEW_TABLES, &tablenames );
      if (i < 0) {
         fprintf(stdout, "datascopeOpen: dbquery2 Error: %i\n",i);
         freeDatascopeStateInfo(datascopeSI);
         return(i);
      }
    } else {
	i = dbquery( *datascopedb, dbTABLE_NAME, &tablename );
      if (i < 0) {
         fprintf(stdout, "datascopeOpen: dbquery3 Error: %i\n",i);
         freeDatascopeStateInfo(datascopeSI);
         return(i);
      }
      tablenames = strtbl( tablename, 0 );
    }

    DATASCOPE_DEBUG("Getting Records\n"); 
    
    request_fieldnames = newtbl( 0 );
    
    for( itable = 0; itable < maxtbl( tablenames ); itable++ ) {
      
      tablename = gettbl( tablenames, itable );
     if (tablename == NULL) {
         fprintf(stdout, "datascopeOpen: gettable Error fo itable=%i and maxtabl=%i\n",itable,maxtbl(tablenames));
         freeDatascopeStateInfo(datascopeSI);
         return(MDAS_FAILURE);
      }
      DATASCOPE_DEBUG("datascopeOpen: TableName =%s\n",tablename) ;

      dbtemp = dblookup( *datascopedb, 0, tablename, 0, 0 );
fprintf(stdout,"datascopeOpen: TableId=%i\n",dbtemp.table);fflush(stdout);
      if (dbtemp.table < 0) {
                 fprintf(stdout, "datascopeOpen: dblookup Error db.table=%i\n",dbtemp.table);
         i=dbtemp.table;
         freeDatascopeStateInfo(datascopeSI);
         return(i);
      }

      i = dbquery( dbtemp, dbTABLE_FIELDS, 
	       &table_fieldnames );
     if (i < 0) {
         fprintf(stdout, "datascopeOpen: dbquery4 Error: %i\n",i);
         freeDatascopeStateInfo(datascopeSI);
         return(i);
      }

      DATASCOPE_DEBUG("datascopeOpen: DbQuery Result =%i and maxtbl(table_fieldnames)=%i\n",
	i,maxtbl(table_fieldnames)) ;

      for( ifield = 0;
	   ifield < maxtbl( table_fieldnames );
	   ifield++ ) {
	sprintf( fieldname, "%s.%s",
		 tablename,
		 gettbl( table_fieldnames, ifield ) );
      DATASCOPE_DEBUG("datascopeOpen: TableFieldName[%i] =%s\n",ifield,fieldname) ;

	pushtbl( request_fieldnames, strdup( fieldname ) );
      }
    }
    datascopeSI->requestFieldNames = request_fieldnames;
  }
  
  if (datascopeSI->tmpFileName  != NULL) {
      /* we are doing an extfile if string > 0 length */
      DATASCOPE_DEBUG("datascopeOpen: dbfile/dbextfile for '%s'\n",datascopeSI->tmpFileName);
      strcpy(fileName,"");
      if (strlen(datascopeSI->tmpFileName) > 0) 
	  i =  dbextfile( *datascopedb, datascopeSI->tmpFileName,
			  fileName);
      else
	  i =  dbfilename(*datascopedb, fileName);
      DATASCOPE_DEBUG("datascopeOpen: dbfile/dbextfile Result= %i\n",i);
      DATASCOPE_DEBUG("datascopeOpen: dbfile/dbextfile path= %s\n",fileName);
      if (i < 0){
	  fprintf(stdout,"datascopeOpen: dbfile/dbextfile path= %s\n",fileName);
	  fflush(stdout);
	  return(MDAS_FAILURE);
      }
      abspath(fileName,fileName2);
      free(datascopeSI->tmpFileName);
      datascopeSI->tmpFileName = NULL;
      DATASCOPE_DEBUG("datascopeOpen: dbfile/dbextfile absolute path= %s\n",fileName2);
      is_view = 1;
      datascopeSI->dbfilefd = fopen(fileName2,"r");
      if (datascopeSI->dbfilefd == NULL) {
	  fprintf(stdout,"datascopeOpen: dbfile/dbextfile  unable to open local file: %s\n",fileName2);
	  fflush(stdout);
      }
  }



  datascopeSI->dbPtrPtr = datascopedb;

  if (is_view != 0)
     datascopeSI->isView = 1;
  else
     datascopeSI->isView = 0;
  datascopeSI->tmpFileName = NULL;
  datascopeSI->xml_bns = NULL;
  datascopeSI->firstRead = 1;
  mdDesc->driverSpecificInfo = (char *) datascopeSI;
  DATASCOPE_DEBUG("datascopeOpen: Finish.\n");


}

/* datascopeCreate - Handles the create call.
 *
 * Input :  MDriverDesc *mdDesc - The datascope descriptor handle
 *         char *datascopePathDesc - The datascope path name to be opened
 *         int datascopeMode - The datascope mode
 *
 * Output : Returns the datascope descriptor of the new datascope.
 */

/*
int
datascopeCreate(MDriverDesc *mdDesc, mdasResInfo *rsrcInfo, char *datascopePathDesc, int datascopeMode, , char *userName)
*/
int
datascopeCreate(MDriverDesc *mdDesc, char *rsrcInfo, char *datascopePathDesc, int datascopeMode, char *userName)
{
  int status;

  return(FUNCTION_NOT_SUPPORTED);

}

/* datascopeClose - Handles the close call.
 *
 * Input : MDriverDesc *mdDesc - The datascope descriptor to be closed
 *
 * Output : Return status of close
 */

int
datascopeClose(MDriverDesc *mdDesc)
{
  int status;
  datascopeStateInfo *datascopeSI;

  DATASCOPE_DEBUG("datascopeClose: Begin\n");

  datascopeSI = (datascopeStateInfo *) mdDesc->driverSpecificInfo;
  if (datascopeSI->isView) {
      if (datascopeSI->firstRead > 1)
	  fclose( (FILE *) datascopeSI->firstRead);
  }
  if (datascopeSI->dbfilefd !=NULL)
      fclose( (FILE *) datascopeSI->dbfilefd);
  if (datascopeSI->tmpFileName != NULL){
	unlink(datascopeSI->tmpFileName);
	free(datascopeSI->tmpFileName);
  } 
  if (datascopeSI->xml_bns  != NULL)
     free(datascopeSI->xml_bns);
  freeDatascopeStateInfo(datascopeSI);
  DATASCOPE_DEBUG("datascopeClose: End\n");
  return (MDAS_SUCCESS);
}

/* datascopeRead - Handles the read call.
 *
 * Input : MDriverDesc *mdDesc - The datascope descriptor to read
 *	   char *buffer - The input buffer
 *	   int amount - The amount to read
 *
 * Output : Returns to number of bytes read
 */

int
datascopeRead(MDriverDesc *mdDesc, char *buffer, int length)
{
  int	status;
  int             datascope ,i ,ii;
    int             pktid ; 
    char            srcname[MAX_TOKEN] ;
    double          vdatascopetime ;
    char           *vdatascopepacket=0 ; 
    int             nbytes = 0 ;
    int             bufsize=0 ;
    datascopeStateInfo   *datascopeSI;
    Dbptr *datascopedbPtr;
    Bns     *xml_bns;	
    int first;
    FILE *tmpFileFd;
    char tmpFileName[400];
    char *mybuffer;
    int mylength;
    int mysize = 0;
    int packcount;
    char *xmlStrPtr;

    datascopeSI = (datascopeStateInfo *) mdDesc->driverSpecificInfo;
    datascopedbPtr = datascopeSI->dbPtrPtr;

    mylength = length;
    mybuffer = buffer;
    first = datascopeSI->firstRead;
  DATASCOPE_DEBUG("datascopeRead: Start Reading: isView=%i and firstRead=%i,buffer length = %i\n",
	datascopeSI->isView,datascopeSI->firstRead,length);

    if ( datascopeSI->dbfilefd != NULL && datascopeSI->firstRead != 1) {
	i = fread(buffer,1,length,datascopeSI->dbfilefd);
	return(i);
    }

   if (datascopeSI->isView) {
    if (datascopeSI->presentation != NULL && !strcmp(datascopeSI->presentation,"db2xml")) {
      if (datascopeSI->firstRead == 1) {
	  datascopeSI->firstRead = -1;
  DATASCOPE_DEBUG("datascopeRead: Performing db2xml\n");
	i = db2xml( *datascopedbPtr,  "VORBVIEW", "VORBROW",
              datascopeSI->requestFieldNames, 0,(void **) &xml_bns, DBXML_BNS ); 
  DATASCOPE_DEBUG("datascopeRead: After db2xml:%i \n",i);
        if (i < 0 || bnscnt( xml_bns ) <= 0 ) {
          fprintf(stdout,"datascopeRead: Error in  db2xml: error=%i, bnscnt=%i\n",
		bnserrno(xml_bns),bnscnt( xml_bns ));
        }
       	datascopeSI->xml_bns = xml_bns;
      } 
      else {
        xml_bns = datascopeSI->xml_bns;
      }      
      i = bns2buf( xml_bns, (void *) buffer,  length );
/*	i =  bnsget(xml_bns,(void *) buffer, BYTES, length );  */
      if (i  < length) {
	  bnsclose( xml_bns);
	  datascopeSI->xml_bns = NULL;
      }
  DATASCOPE_DEBUG("datascopeRead: BufferLength= %i \n",i);
      return(i);
    }
    else if (datascopeSI->presentation != NULL && !strcmp(datascopeSI->presentation,"dbfilename")) {
	tmpFileFd = (FILE *)  datascopeSI->dbfilefd;
	datascopeSI->firstRead = -1;
	i = fread(buffer,1,length,tmpFileFd);
  DATASCOPE_DEBUG("datascopeRead: BufferLength= %i \n",i);
	return(i);
    }
    else {
  DATASCOPE_DEBUG("datascopeRead: performing dbselect\n") ;
      if (datascopeSI->firstRead == 1) {
        sprintf(tmpFileName,"../data/dataScopeViewSelect.%i",getpid());
        tmpFileFd = fopen(tmpFileName,"w");
        if (tmpFileFd == NULL) {
           fprintf(stdout, "datascopeRead:  Unable to open temp file:%s\n",tmpFileName);        
          return(DB_TAB_OPEN_ENV_ERROR);
       }
  DATASCOPE_DEBUG("datascopeRead: performing dbselect\n") ;
       dbselect (*datascopedbPtr, datascopeSI->requestFieldNames, tmpFileFd ) ;
  DATASCOPE_DEBUG("datascopeRead: tmpFile position = %d\n",ftell(tmpFileFd )) ;
       fclose(tmpFileFd ) ;
       tmpFileFd = fopen(tmpFileName,"r");
       datascopeSI->tmpFileName = strdup(tmpFileName);   
       datascopeSI->firstRead = (int) tmpFileFd;
     }
     else {
       tmpFileFd = (FILE *)  datascopeSI->firstRead;
     }
     i = fread(buffer,1,length,tmpFileFd);
  DATASCOPE_DEBUG("datascopeRead: BufferLength= %i \n",i);
     return(i);
    }

   }
   else {
    status = dbget(*datascopedbPtr,buffer);
    if (status < 0)
      return(status);
    return (strlen(buffer));

   }

}

/* datascopeWrite - Handles the write call.
 *
 * Input : MDriverDesc *mdDesc - The datascope descriptor to write
 *         char *buffer - The output buffer
 *         int amount - The amount to write
 *
 * Output : Returns to number of bytes written
 */

int
datascopeWrite(MDriverDesc *mdDesc, char *buffer, int length)
{
    int	status;
    datascopeStateInfo   *datascopeSI;
    Dbptr *datascopedbPtr;
    char *mybuffer, *tmpPtr;
    int mylength;
    int i,ii;
    char *tableName;
    char *attrName[MAX_TABLE_COLS];
    char *attrVal[MAX_TABLE_COLS];
    datascopeSI = (datascopeStateInfo *) mdDesc->driverSpecificInfo;
    datascopedbPtr = datascopeSI->dbPtrPtr;
    mylength = length;
    mybuffer = buffer;
  DATASCOPE_DEBUG("datascopeWrite: Start Writing\n");
    if (datascopeSI->presentation != NULL && 
	!strcmp(datascopeSI->presentation,"xml2db")) {
      while (mybuffer) {
	i = getDatascopeTableRowFromXML(tableName,attrName,attrVal, 
			       &mybuffer,mylength, "vorb.schema");
	if (i < 0) {
	  if (i != DATASCOPE_ROW_INCOMPLETE)
	    return(i);
  DATASCOPE_DEBUG("Row:%s\n",tmpPtr);
	  return(i);
	}
      }
    }
    else {
      while (mybuffer && mylength > 0) {
	tmpPtr = mybuffer;
	i = getDatascopeTableRowFromTxt(tableName, 
			       &mybuffer,mylength);
	if (i < 0) {
	  if (i != DATASCOPE_ROW_INCOMPLETE)
	    return(i);
  DATASCOPE_DEBUG("Row:%s\n",tmpPtr);
	   return(i);
	}
	/*
	i = dbput (*datascopedbPtr, tmpPtr);
	*/
  DATASCOPE_DEBUG("Row:%s\n",tmpPtr);
	if (i < 0)
	  return (i);
	mylength = mylength - (int) (tmpPtr - mybuffer);
      }
    }
    return (length);
}

/* datascopeSeek - Handles the seek call.
 *
 * Input : MDriverDesc *mdDesc - The datascope descriptor to seek
 *         int offset - The position of the next operation
 *         int whence - Same definition as in datascope.
 *              SEEK_SET - pointer is set to the value of the Offset parameter.
 *              SEEK_CUR - pointer is set to its current location plus the
 *                      value of the Offset parameter.
 *              SEEK_END - pointer is set to the size of the datascope plus the
 *                      value of the Offset parameter.
 *
 * Output : Returns the status of seek
 */

srb_long_t
datascopeSeek(MDriverDesc *mdDesc, srb_long_t offset, int whence)
{
    srb_long_t	status;
    srb_long_t seekPos;
    return(FUNCTION_NOT_SUPPORTED);

}

/* datascopeUnlink - Handles the unlink call.
 *
 * Input : char *datascopeDesc - The datascope path name to unlink
 *
 * Output : Returns the status of unlink
 */

int
datascopeUnlink(char *rsrcAddress, char *datascopePathDesc)
{
    int status;
 
        return(FUNCTION_NOT_SUPPORTED);
}

int 
datascopeProc(MDriverDesc *mdDesc, char *procName, 
              char *inBuf, int inLen, 
              char *outBuf, int outLen )
{

  int status = 0;
  char *argv[MAX_PROC_ARGS_FOR_DS];
  int             datascope ,i ,ii,j,k,l, numArgs;
  datascopeStateInfo   *datascopeSI;
  Dbptr *datascopedbPtr;
  Tbl  *processTable;
  Tbl  *exprTable;
  Arr  *exprArray;
  char *tmpPtr, *tmpPtr1, *retStr;
  Dbptr *datascopedbPtr2;
  Dbptr  dbPtr1;
  int  outBufStrLen;
  Bns     *xml_bns;
  char fileNameString[FILENAME_MAX];
  char fileNameString2[FILENAME_MAX];
  int fldType;
  char *tableName;  
  Dbvalue tmpDbValue;
  FILE *tmpfd;
  Expression *exprPtr;
  char tmpBuf[STRSZ * 2];


  datascopeSI = (datascopeStateInfo *) mdDesc->driverSpecificInfo;
  datascopedbPtr = datascopeSI->dbPtrPtr;
  outBufStrLen =  0;
  outBuf[0] = '\0';
  DATASCOPE_DEBUG("datascopeProc: Begin Proc inLen=%i,outLen=%i \n",inLen,outLen);
  DATASCOPE_DEBUG("datascopeProc: procName=$$%s$$\n",procName);
  DATASCOPE_DEBUG("datascopeProc: inBuf=$$%.80s$$\n",inBuf);
  
  if (isalnum(procName[0]) == 0)
      i = getArgsFromString(procName +1 ,argv,procName[0]);
  else
      i = getArgsFromString(procName,argv,'|');
  DATASCOPE_DEBUG("datascopeProc: i=%i, actualprocName=$$%s$$\n",i,procName);
  if(i == 0 )
      return(FUNCTION_NOT_SUPPORTED);
  if (i < 0) 
      return(i);
  numArgs = i;
  i = 0;
  if (!strcmp(argv[0],"get_dbptr")) {
      /* Returns outBuf = datascopedbPtr String */
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"put_dbptr")) {
      /* inBuf = datascopedbPtr String */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      return(i);
  }
  else if (!strcmp(argv[0],"dbopen_table")) {
      /* argv[1] = table_name 
         argv[2] = mode */
      /* inBuf = datascopedbPtr String */
      /* Returns outBuf = datascopedbPtr String */
      if (inLen > 0) 
	  str2dbPtr(inBuf,datascopedbPtr);
      i = dbopen_table (argv[1], argv[2], datascopedbPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbfind")) {
      /* argv[1] = searchstring
         argv[2] = flag (int) */
      /* inBuf = datascopedbPtr String */
      /* Returns outBuf = status|datascopedbPtr String */
      if (inLen > 0) 
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbfind( *datascopedbPtr, argv[1], atoi(argv[2]), NULL);
      sprintf(outBuf,"%i|%i|%i|%i|%i",i,
			datascopedbPtr->database,
			datascopedbPtr->table,
			datascopedbPtr->field,
			datascopedbPtr->record);
     /* outBufStrLen = dbPtr2str(datascopedbPtr, &outBuf[strlen(outBuf)]);*/
	fprintf(stdout, "outBuf in dbfind proc call is <%s>\n", outBuf);fflush(stdout);
      outBufStrLen = strlen(outBuf)+1;
  }  
  else if (!strcmp(argv[0],"dblookup")) {
      /* argv[1] = database_name
	 argv[2] = table_name 
	 argv[3] = field_name 
	 argv[4] = record_name */
      /* inBuf = datascopedbPtr String */
      /* Returns outBuf = datascopedbPtr String */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      *datascopedbPtr = dblookup(*datascopedbPtr, argv[1],argv[2],argv[3],argv[4]);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"db2xml")) {
      /* argv[1] = rootnode
	 argv[2] = rownode
	 argv[3] = flag (int)
	 argv[4] = fields separated by ;;
	 argv[5] = expressions separated by ;; */
      /* inBuf = datascopedbPtr String */
      /* Returns outBuf = if flag= 0 returns xml string
                          if flag=DBXML_BNS return (BNS *) */
      /* return status for the function gives size of the outBuf fille */
      /* if return status = outLen-1
             when flag = 0 use dbReadString to get rest of string
	     when flag =DBXML_BNS use dbReadBns to get rest of string
	        one can use dbRead* as many times as wanted until
		the return status is 0 or negative */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      if (strlen(argv[4]) == 0)
	  processTable = NULL;
      else {
	  processTable =  newtbl( 0 );
	  tmpPtr1 = argv[4];
	  while ((tmpPtr  =  strstr(tmpPtr1,";;")) != NULL) {
	      *tmpPtr = '\0';
	      strtrim(tmpPtr1);
	      pushtbl( processTable,strdup(tmpPtr1) );
	      tmpPtr1 = tmpPtr + 2;
	  }
	  strtrim(tmpPtr1);
	  pushtbl( processTable,strdup(tmpPtr1) );
      }
      if (strlen(argv[5]) == 0)
          exprTable = NULL;
      else {
          exprTable =  newtbl( 0 );
          tmpPtr1 = argv[4];
          while ((tmpPtr  =  strstr(tmpPtr1,";;")) != NULL) {
              *tmpPtr = '\0';
              strtrim(tmpPtr1);
              pushtbl( exprTable,strdup(tmpPtr1) );
              tmpPtr1 = tmpPtr + 2;
          }
          strtrim(tmpPtr1);
          pushtbl( exprTable,strdup(tmpPtr1) );
      }
      if (atoi(argv[3]) == DBXML_BNS) {
	  i = db2xml(*datascopedbPtr,argv[1],argv[2],
                     processTable, exprTable,
		     (void **) &xml_bns, DBXML_BNS );
  DATASCOPE_DEBUG("datascopeProc: db2xml-bns:status= %i,bnscnt=%i\n",
		  i,bnscnt(xml_bns));
	  if (i < 0 || bnscnt( xml_bns ) <= 0) {
	      fprintf(stdout,"datascopeRead: Error in  db2xml: error=%i, bnscnt=\%i\n",
		      bnserrno(xml_bns),bnscnt( xml_bns ));
	      return(i);
	  }
	  sprintf(outBuf,"%i",xml_bns );
	  return(strlen(outBuf));
      }
      else {
	  i = db2xml(*datascopedbPtr,argv[1],argv[2], 
		     processTable, exprTable, (void **) &retStr, 0);
	  if (i < 0)
	      return(i);
	  if ((i = strlen(retStr)) <= (outLen - 1)) {
	      strcpy(outBuf,retStr);
	      datascopeSI->db2xmlOrigStr = NULL;
	      datascopeSI->db2xmlRemStr =  NULL;
	      return(i);
	  }
	  else {
	      strncpy(outBuf,retStr,outLen);
	      datascopeSI->db2xmlOrigStr = retStr;
	      datascopeSI->db2xmlRemStr = retStr + outLen;
	      return(outLen);
	  }
      }
  }
  else if (!strcmp(argv[0],"dbReadString")) {
      /* return outBuf with the string (as much as possible  */
      /* return status of function is the length of used outBuf */ 
      if (datascopeSI->db2xmlRemStr == NULL)
	  return(0);
      retStr = datascopeSI->db2xmlRemStr;
      if ((i = strlen(retStr)) <= (outLen-1)) {
	  strcpy(outBuf,retStr);
	  free(datascopeSI->db2xmlOrigStr);
	  datascopeSI->db2xmlOrigStr = NULL;
	  datascopeSI->db2xmlRemStr =  NULL;
	  return(i);
      }
      else {
	  strncpy(outBuf,retStr,outLen);
	  datascopeSI->db2xmlRemStr = retStr + outLen;
	  return(outLen);
      }
  }
  else if (!strcmp(argv[0],"dbReadBns")) {
      /* return outBuf with the string (as much as possible  */
      /* return status of function is the length of used outBuf */
      xml_bns = (Bns *) atoi(argv[1]);
      i = bns2buf( xml_bns, (void *) outBuf,  outLen - 1 );
      return(i);
  }
  else if (!strcmp(argv[0],"dbprocess")) {
      /* argv[1] = statements separated by ;; */
      /* inBuf = datascopedbPtr String */
      /* Returns outBuf = datascopedbPtr String */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      processTable =  newtbl( 0 );
      tmpPtr1 = argv[1];
      while ((tmpPtr  =  strstr(tmpPtr1,";;")) != NULL) {
	  *tmpPtr = '\0';
	  strtrim(tmpPtr1);
  	  DATASCOPE_DEBUG("datascopeProc: process Stmt=%s\n",tmpPtr1);
	  pushtbl( processTable,strdup(tmpPtr1) );
	  tmpPtr1 = tmpPtr + 2;
      }
      strtrim(tmpPtr1);
      DATASCOPE_DEBUG("datascopeProc: process Stmt=%s\n",tmpPtr1);
      pushtbl( processTable,strdup(tmpPtr1) );
      *datascopedbPtr = dbprocess(*datascopedbPtr,processTable,dbinvalid);

      if (datascopedbPtr->database < 0) {
	  return(datascopedbPtr->database);
      }
      datascopeSI->dbPtrPtr = datascopedbPtr;
      datascopeSI->requestFieldNames = 0;
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbfilename")) {
      /* outBuf contains the  a pair separated by | :          	 status|fileName  */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      strcat(outBuf,"               ");
      i = dbfilename(*datascopedbPtr, fileNameString);
	fprintf(stdout, "dbfilename returns %s\n", fileNameString ); fflush(stdout);
      abspath(fileNameString,fileNameString2);
      sprintf(outBuf,"%i|%s",i,fileNameString2);
	fprintf(stdout, "ready to return %s\n", outBuf ); fflush(stdout);
      return(strlen(outBuf));
  }
  else if (!strcmp(argv[0],"dbextfile")) {
      /* argv[1] = tablename */
      /* outBuf contains the  a pair separated by | :   status|fileName  */
      /* if you need the dbPtr info you need to make another call after this */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      strcat(outBuf,"               ");
      i = dbextfile(*datascopedbPtr,argv[1], fileNameString);
      abspath(fileNameString,fileNameString2);
	  sprintf(outBuf,"%i|%s",i,fileNameString2);
      return(strlen(outBuf));
  }
  else if (!strcmp(argv[0],"dbget")) {
      /* returns the dbgetv result in outBuf  */
      /* if you need the dbPtr info you need to make another call after this */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbget(*datascopedbPtr,outBuf);
      if (i < 0)
	  return(i);
      else
	  return(strlen(outBuf));
  }
  else if (!strcmp(argv[0],"dbgetv")) {
      /* argv[1] = tablename zerolength string if not given */
      /* argv[2] thru argv[numArgs-1]  fieldNames */
      /* inBuf = datascopedbPtr String */
      /* Returns outBuf = contains d|v0|v1|...|v[numArgs-2]  where
	 d = datascopedbPtr String 
         v[i] is the value being returned \| is used escape any | inside the string values*/

      Dbvalue dbValueArr[numArgs];
      if (numArgs == 2) {
	  fprintf(stdout, "datascopeproc: in dbgetv  number of fields is zero:\n");
	  return(MDAS_FAILURE);
      }
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      if (strlen(argv[1]) > 0)
	  tableName = argv[1];
      else
	  tableName = NULL;
      
      for (i = 0; i < numArgs -2; i++)
	  argv[i] = argv[i+2];
      numArgs  = numArgs - 2;

      i  =  makeDbgetvCall (datascopedbPtr, tableName, numArgs, argv, dbValueArr);
      if (i < 0) {
	  fprintf(stdout, "datascopeproc: in dbgetv makeDbgetvCall Error : %i\n", i);
	  return(i);
      }
      dbPtr2str(datascopedbPtr,outBuf);
      dbPtr1 = *datascopedbPtr;
      if (tableName != NULL) {
	  dbPtr1 = dblookup( dbPtr1, 0, tableName, 0, 0 );
	  if (dbPtr1.table < 0) {
	      fprintf(stdout, "datascopeproc: in dbgetv  dblookup Error db.table=%i\n",dbPtr1.table);
	      return(dbPtr1.table);
	  }
      }
      for (ii =  0 ; ii < numArgs; ii++) {
	  dbPtr1 = dblookup( dbPtr1, "", "", argv[ii], "" );
	  if (dbPtr1.table < 0) {
	      fprintf(stdout, "datascopeproc: in dbgetv  dblookup for field %s Error db.table=%i\n",
		      argv[ii], dbPtr1.table);
	      return(dbPtr1.table);
	  }
	  i = dbquery( dbPtr1, dbFIELD_TYPE, &fldType);
	  if (i < 0) {
	      fprintf(stdout, "datascopeproc: in dbgetv getting field types using dbquery Error: %i\n",i);
	      return(i);
	  }
	  switch(fldType) {
	      case dbDBPTR:
		  sprintf(tmpBuf, "%d %d %d %d",
			  dbValueArr[ii].db.database,
			  dbValueArr[ii].db.table,
			  dbValueArr[ii].db.field,
			  dbValueArr[ii].db.record );
		  break;
	      case dbSTRING:
		  l = strlen(dbValueArr[ii].s);
		  for (i = 0, j=0; i <= l ;i++,j++) {
		      if (dbValueArr[ii].s[i] == '|') {
			  tmpBuf[j] = '\\';
			  j++;
		      }
		      tmpBuf[j] = dbValueArr[ii].s[i];
		  }
		  
		  break;
	      case dbBOOLEAN:
	      case dbINTEGER:
	      case dbYEARDAY:
		  sprintf(tmpBuf, "%d", dbValueArr[ii].i );              
		  break;
	      case dbREAL:
	      case dbTIME:
		  sprintf(tmpBuf, "%f", dbValueArr[ii].d );                                              
		  break;
	      default: 
		  sprintf(tmpBuf,"");
		  break;    
	  }	  
	  strcat(outBuf,"|");
	  strcat(outBuf,tmpBuf);
      }
      i = 0;
      outBufStrLen = strlen(outBuf);
  }
  else if (!strcmp(argv[0],"dbput")) {
      /* argv[1] contains put string */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      if (strlen(argv[1]) > 0)
	  i = dbput(*datascopedbPtr,argv[1]);
      else
	  i = dbput(*datascopedbPtr, 0);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbputv") || !strcmp(argv[0],"dbaddv")) {
      /* argv[1] = tablename */
      /* for i = 2,5,8,11,...
         argv[i]   = fieldName
	 argv[i+1] = fieldType (integer :dbREAL,dbINTEGER, etc)
         argv[i+2] = field Value */

      if (numArgs == 2) {
          fprintf(stdout, "datascopeproc: in dbputv/dbaddv  number of fields is zero:\n");
          return(MDAS_FAILURE);
      }
      if ((numArgs -2) % 3 != 0){
          fprintf(stdout, "datascopeproc: in dbputv/dbaddv <name|type|value> triplets required\n");
	  return(MDAS_FAILURE);
      }
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      if (strlen(argv[1]) > 0)
          tableName = argv[1];
      else
          tableName = NULL;
      if (!strcmp(argv[0],"dbaddv")) 
	  *datascopedbPtr = dblookup(*datascopedbPtr,"", "", "", "dbSCRATCH" );
      for ( i = 2; i  < numArgs; i + 3) {
	  tmpDbValue.t = NULL;
	  switch(atoi(argv[i+1])) {
	      case dbDBPTR:
		  l = strlen(argv[i+2]);
		  for (ii = 0; ii < l ; ii++) {
		      if (argv[i+2][ii] == ' ' && argv[i+2][ii+1] != ' ')
			  argv[i+2][ii] = '|';
		  }
		  str2dbPtr(argv[i+2],&(tmpDbValue.db));
		  break;
	      case dbSTRING:
		  l = strlen(argv[i+2]);
		  for (ii = 0, j=0; ii <= l ;ii++,j++) {
		      if (argv[i+2][ii] == '\\' && argv[i+2][ii+1] == '|')
			  ii++;
		      tmpDbValue.s[j] == argv[i+2][ii];
		  }
		  break;
	      case dbBOOLEAN:
              case dbINTEGER:
              case dbYEARDAY:
		  tmpDbValue.i = (int) strtol(argv[i+2],(char**)NULL, 10);
                  break;
              case dbREAL:
              case dbTIME:
		  tmpDbValue.d = strtod(argv[i+2],(char**)NULL);
                  break;
              default:
		  fprintf(stdout, "datascopeproc: in dbputv/dbaddv unknown fieldType:%i\n",atoi(argv[i+1]));
		  return(MDAS_FAILURE);
                  break;
          }
	  ii = dbputv(*datascopedbPtr,tableName,argv[i],tmpDbValue);
	  if (ii < 0) 
	      return(ii);
      }
      if (!strcmp(argv[0],"dbaddv")) 
          i = dbaddchk(*datascopedbPtr,0);
      else
	  i = 0;
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbquery")) {
      /* argv[1] = code in integer */
      char tmpBuf[STRSZ * 2];
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      switch (atoi(argv[1])) {
	  case dbDATABASE_COUNT:
	  case dbTABLE_COUNT:
	  case dbFIELD_COUNT:
	  case dbRECORD_COUNT:
	  case dbTABLE_SIZE:
	  case dbFIELD_SIZE:
	  case dbRECORD_SIZE:
	  case dbFIELD_TYPE:
	  case dbFIELD_INDEX:
	  case dbVIEW_TABLE_COUNT:
	  case dbTABLE_IS_VIEW:
	  case dbTABLE_IS_WRITABLE:
	  case dbTABLE_IS_ADDABLE:
	  case dbDATABASE_IS_WRITABLE:
	  case dbTABLE_ADDRESS:
	  case dbTABLE_IS_TRANSIENT:
          case dbLOCKS:
	      ii =  dbquery(*datascopedbPtr,atoi(argv[1]), &i);
	      if (ii < 0)
		  return(ii);
	      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
	      sprintf(tmpBuf,"|%i",i);
	      strcat(outBuf,tmpBuf);
	      i = 0;
	      outBufStrLen = strlen(outBuf);
	      break;
	  case dbSCHEMA_DESCRIPTION:
	  case dbDATABASE_DESCRIPTION:
	  case dbTABLE_DESCRIPTION:
	  case dbFIELD_DESCRIPTION:
	  case dbSCHEMA_DETAIL:
	  case dbDATABASE_DETAIL:
	  case dbTABLE_DETAIL:
	  case dbFIELD_DETAIL:
	  case dbSCHEMA_NAME:
	  case dbDATABASE_NAME:
	  case dbTABLE_NAME:
	  case dbFIELD_NAME:
	  case dbFIELD_FORMAT:
	  case dbFIELD_UNITS:
	  case dbNULL:
	      ii =  dbquery(*datascopedbPtr,atoi(argv[1]),&tmpPtr);
              if (ii < 0)
                  return(ii);
              outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
              sprintf(tmpBuf,"|%s",tmpPtr);
              strcat(outBuf,tmpBuf);
              i = 0;
              outBufStrLen = strlen(outBuf);
	      break;
	  case dbFIELD_RANGE:
	  case dbDATABASE_FILENAME:
	  case dbTABLE_FILENAME:
	  case dbTABLE_DIRNAME:
	  case dbDBPATH:
	  case dbFORMAT:
	  case dbUNIQUE_ID_NAME:
          case dbFIELD_BASE_TABLE:
          case dbTIMEDATE_NAME:
          case dbIDSERVER:
	      ii =  dbquery(*datascopedbPtr,atoi(argv[1]),(char *) tmpBuf+1);
	      if (ii < 0)
                  return(ii);
              outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
	      *tmpBuf ='|';
              strcat(outBuf,tmpBuf);
              i = 0;
              outBufStrLen = strlen(outBuf);
              break;
	  case dbVIEW_TABLES:
	  case dbPRIMARY_KEY:
	  case dbALTERNATE_KEY:
	  case dbFOREIGN_KEYS:
	  case dbTABLE_FIELDS:
	  case dbFIELD_TABLES:
	  case dbSCHEMA_FIELDS:
	  case dbSCHEMA_TABLES:
	      ii =  dbquery(*datascopedbPtr,atoi(argv[1]),&exprTable);
	      if (ii < 0)
                  return(ii);
	      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
	      dbTable2str(exprTable,(char *)(outBuf + strlen(outBuf)));
	      i = 0;
              outBufStrLen = strlen(outBuf);
	      break;
	  case dbLINK_FIELDS:
	  case dbLASTIDS:
	      ii =  dbquery(*datascopedbPtr,atoi(argv[1]),&exprArray);
              if (ii < 0)
                  return(ii);
              outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
              dbArray2str(exprArray,(char *)(outBuf + strlen(outBuf)));
              i = 0;
              outBufStrLen = strlen(outBuf);
	      break;
	  default:                                                                                                   
	      fprintf(stdout, "datascopeproc: in dbquery unknown code:%i\n",atoi(argv[1]));                    
	      return(MDAS_FAILURE);                                                                                  
	      break;                                                                                                 
      }
  }
  else if (!strcmp(argv[0],"dbfilename_retrieve")) {
      /* outBuf contains the  a pair separated by | :            status|fileName  */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      strcat(outBuf,"               ");
      i = dbfilename(*datascopedbPtr, fileNameString);
        fprintf(stdout, "dbfilename returns %s\n", fileNameString ); fflush(stdout);
      abspath(fileNameString,fileNameString2);
      datascopeSI->dbfilefd = fopen(fileNameString2,"r");
      if (datascopeSI->dbfilefd == NULL) {
          fprintf(stdout,"datascopeproc: in dbfilename_retrieve  unable to open local file: %s\n",fileNameString2);
          fflush(stdout);
      }
      datascopeSI->firstRead = -1;
      i = fread(outBuf,1,outLen,datascopeSI->dbfilefd);
      return(i);
  }
  else if (!strcmp(argv[0],"dbextfile_retrieve")) {
      /* argv[1] = tablename */
      /* outBuf contains the  data retieved from the file  */
      /* if you need the dbPtr info you need to make another call after this */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      strcat(outBuf,"               ");
      i = dbextfile(*datascopedbPtr,argv[1], fileNameString);
      abspath(fileNameString,fileNameString2);
      datascopeSI->dbfilefd = fopen(fileNameString2,"r");
      if (datascopeSI->dbfilefd == NULL) {
          fprintf(stdout,"datascopeproc: in dbextfile_retrieve  unable to open local file: %s\n",fileNameString2);
          fflush(stdout);
      }
      datascopeSI->firstRead = -1;
      i = fread(outBuf,1,outLen,datascopeSI->dbfilefd);
      return(i);
  }
  else if (!strcmp(argv[0],"dbadd")) {
      /* argv[1] contains add string */
      if (inLen > 0)
	  str2dbPtr(inBuf,datascopedbPtr);
      if (strlen(argv[1]) > 0)
	  i = dbadd(*datascopedbPtr,argv[1]);
      else
	  i = dbadd(*datascopedbPtr, 0);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbadd_remark")) {
      /* argv[1] contains remark string */
      if (inLen > 0)
	  str2dbPtr(inBuf,datascopedbPtr);
      i = dbadd_remark(*datascopedbPtr,argv[1]);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbget_remark")) {
      if (inLen > 0)
	  str2dbPtr(inBuf,datascopedbPtr);
      i = dbget_remark(*datascopedbPtr, &tmpPtr);
      if (i < 0)
	  return(i);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
      strcat(outBuf,"|");
      strcat(outBuf,tmpPtr);
      free(tmpPtr);
      outBufStrLen = strlen(outBuf);
  }
  else if (!strcmp(argv[0],"dbaddchk")) {
      /* argv[1] contains add string */
      if (inLen > 0)
	  str2dbPtr(inBuf,datascopedbPtr);
      if (strlen(argv[1]) > 0)
	  i = dbaddchk(*datascopedbPtr,argv[1]);
      else
	  i = dbaddchk(*datascopedbPtr, 0);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbaddnull")) {
      if (inLen > 0)
	  str2dbPtr(inBuf,datascopedbPtr);
      i = dbaddnull(*datascopedbPtr);
      if (i < 0)
	  return(i);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
      sprintf(tmpBuf,"|%i",i);
      strcat(outBuf,tmpBuf);
      i = 0;
      outBufStrLen = strlen(outBuf);
  }
  else if (!strcmp(argv[0],"dbaddchk")) {
      /* argv[1] contains schema string */
      if (inLen > 0)
	  str2dbPtr(inBuf,datascopedbPtr);
      if (strlen(argv[1]) > 0)
	  i = dbaddchk(*datascopedbPtr,argv[1]);
      else
	  i = dbaddchk(*datascopedbPtr, 0);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbcompile")) {
      /* argv[1] contains schema  string */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbcompile(*datascopedbPtr,argv[1]);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbselect")) {
      /* argv[1] contains Table expressions each of which
          is separated  by ;;*/
      /* if you need the dbPtr info you need to make another call after this */

      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      processTable =  newtbl( 0 );
      tmpPtr1 = argv[1];
      while ((tmpPtr  =  strstr(tmpPtr1,";;")) != NULL) {
          *tmpPtr = '\0';
          strtrim(tmpPtr1);
          pushtbl( processTable,strdup(tmpPtr1) );
          tmpPtr1 = tmpPtr + 2;
      }
      strtrim(tmpPtr1);
      pushtbl( processTable,strdup(tmpPtr1) );
      sprintf(fileNameString,"/tmp/DSdbselect.%i.%i.%ld.%ld,%ld", 
	      datascopedbPtr->database,datascopedbPtr->table,
	      (long) time(NULL),getpid(), (long) random());
      tmpfd = fopen(fileNameString,"w+");
      i  = 0;
      while (tmpfd == NULL && i < 5) {
	  sprintf(fileNameString2,"%ld", (long) random());
	  strcat(fileNameString,fileNameString2);
	  tmpfd = fopen(fileNameString,"w+");
	  i++;
      }
      if (tmpfd == NULL) {
	  fprintf(stdout,"datascopeProc: dbselect: unable to open ocal tmp file:%s\n",fileNameString);
	      i = -errno;
	      return(i);
      }
      i = dbselect (*datascopedbPtr,processTable, tmpfd);
      if (i < 0) {
	  fclose(tmpfd);
	  unlink(fileNameString);
	  return(i);
      }
      fseek(tmpfd, SEEK_SET, 0);
      i = fread (outBuf, 1,outLen,tmpfd);
      if (i == outLen) {
	  datascopeSI->firstRead = -1;
	  datascopeSI->dbfilefd = tmpfd;
	  return(i);
      }
      else {
	  fclose(tmpfd);
          unlink(fileNameString);
	  return(i);
      }
  }
  else if (!strcmp(argv[0],"dbget_range")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = 0;
      j = 0;
      dbget_range(*datascopedbPtr, &i, &j);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
      sprintf(tmpBuf,"|%i|%i",i,j);
      strcat(outBuf,tmpBuf);
      outBufStrLen = strlen(outBuf);
  }
  else if (!strcmp(argv[0],"dbfree")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbfree (*datascopedbPtr);
      return(i);
  }
  else if (!strcmp(argv[0],"dbclose")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbclose (*datascopedbPtr);
      return(i);
  }
  else if (!strcmp(argv[0],"dbmark")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbmark (*datascopedbPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbdelete")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbdelete (*datascopedbPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbcrunch")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbcrunch (*datascopedbPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbdestroy")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbdestroy (*datascopedbPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbflush_indexes")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbflush_indexes (*datascopedbPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbsave_view")) {
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbsave_view (*datascopedbPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbtruncate")) {
      /* argv[1] containts the integer for truncation */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      j = atoi(argv[1]);
      i = dbtruncate (*datascopedbPtr,j);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbtmp")) {
      /* argv[1] containts the schema string */
      /* a new database pointer is returned */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      *datascopedbPtr = dbtmp (argv[1]);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbstrtype")) {
      /* argv[1] containts the  string */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbstrtype(*datascopedbPtr,argv[1]);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
      sprintf(tmpBuf,"|%i",i);
      strcat(outBuf,tmpBuf);
      outBufStrLen = strlen(outBuf);
  }
  else if (!strcmp(argv[0],"dbex_evalstr")) {
      /* argv[1] containts string to be evaluated
	 argv[2] has type in integer but currently is ignored!
	    everything is coerced as a string */
      /* returns the pair: d|s   where d=dbpointer and s= value as a  string */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbex_evalstr(*datascopedbPtr,argv[1], dbSTRING, &tmpPtr);
      if (i < 0)
	  return(i);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
      strcat(outBuf,"|");
      strcat(outBuf,tmpPtr);
      free(tmpPtr);
      outBufStrLen = strlen(outBuf);
  }
  else if (!strcmp(argv[0],"dbex_compile")) {
      /* argv[1] containts string to be evaluated
         argv[2] has type in integer but currently is ignored! but sent back as part of dbex_eval
	 dbex_compile uses dbSTRING internally */
      /* returns the pair: d|v   where d=dbpointer and v= integer value which is an expression identifier */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      i = dbex_compile(*datascopedbPtr,argv[1], &exprPtr,dbSTRING);
      if (i != 0)
	  return(i);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
      /* 64-BIT PROBLEM NOTICE: Coerce properly the pointer below when using 64-bit */
      sprintf(tmpBuf,"%ld",(long) exprPtr);
      strcat(outBuf,"|");
      strcat(outBuf,tmpPtr);
      outBufStrLen = strlen(outBuf);
      if (datascopeSI->exprArray == NULL) {
	  datascopeSI->exprArray = newarr(0);
      }
      tmpPtr = malloc(10);
      sprintf(tmpPtr,"%i",argv[2]);
      setarr(datascopeSI->exprArray,tmpBuf,tmpPtr);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
  }
  else if (!strcmp(argv[0],"dbex_eval")) {
      /* argv[1] containts expression identifier integer sent by dbex_compile call
         argv[2] has setflag in integer */
      /* if dbex_eval returns dbINVALID the return value is dbINVALID and outBuf is empty */
      /* returns in outBuf the 4-tuple: d|i|j|s   where 
	 d=dbpointer 
	 i= type sent for dbex_compile 
	 j=  return  value from dbex_eval and 
	 s= value as a  string */
      if (inLen > 0)
          str2dbPtr(inBuf,datascopedbPtr);
      /* 64-BIT PROBLEM NOTICE: Coerce properly the pointer below when using 64-bit */
      exprPtr = (Expression *) atoi(argv[1]);
      j =  atoi(argv[2]);
      i = dbex_eval(*datascopedbPtr,exprPtr,j, &tmpPtr);
      if (i == dbINVALID)
	  return(i);
      outBufStrLen = dbPtr2str(datascopedbPtr,outBuf);
      strcat(outBuf,"|");
      strcat(outBuf,tmpPtr);
      free(tmpPtr);
      tmpPtr = getarr(datascopeSI->exprArray, argv[1]);
      sprintf(tmpBuf,"|%s|%i",tmpPtr,i); 
      strcat(outBuf,tmpBuf);
      outBufStrLen = strlen(outBuf);
  }
  else if (!strcmp(argv[0],"dbex_free")) {
      /* argv[1] containts expression identifier integer sent by dbex_compile call */
      if (inLen > 0)
	  str2dbPtr(inBuf,datascopedbPtr);
      /* 64-BIT PROBLEM NOTICE: Coerce properly the pointer below when using 64-bit */
      exprPtr = (Expression *) atoi(argv[1]);
      tmpPtr = (char *) delarr(datascopeSI->exprArray,argv[1]);
      if (tmpPtr != 0)
	  free(tmpPtr);
      i = dbex_free(exprPtr);
      return(i);
  }
  else {
      return(FUNCTION_NOT_SUPPORTED);
  }
  if (i < 0)
      return(i);
  else
      return(outBufStrLen);
}

int
datascopeSync(MDriverDesc *mdDesc)
{
    int status;
 
        return(FUNCTION_NOT_SUPPORTED);
}


/***** datascope utilities ***/

int
freeDatascopeStateInfo(datascopeStateInfo *datascopeSI)
{
  int i;
  Dbptr *db;
  db = datascopeSI-> dbPtrPtr;
  i = dbclose( *db);
  return(i);
}

int
getDatascopeStateInfo(datascopeStateInfo *datascopeSI, char *rsrcInfo,
         char *datascopeDataDesc, int datascopeFlags,
               int datascopeMode, char *userName)
{

  char *dsTable;
  char *dsFind;
  char *dsFindRev;
  char *tmpPtr;
  char *dsposition;
  char *dstimeout;
  char *dsnumofpkts;
  char *dspresentation;
  char *dsnumbulkreads;
  char *dsProcess;
  char *dsfilename;
  dsTable = strstr(datascopeDataDesc,"<DSTABLE>");
  dsFind  = strstr(datascopeDataDesc,"<DSFIND>");
  dsFindRev = strstr(datascopeDataDesc,"<DSFINDREV>");
  dsProcess  = strstr(datascopeDataDesc,"<DSPROCESS>");
  dsposition  = strstr(datascopeDataDesc,"<DSPOSITION>");
  dstimeout  = strstr(datascopeDataDesc,"<DSTIMEOUT>");
  dsnumofpkts  = strstr(datascopeDataDesc,"<DSNUMOFPKTS>");
  dspresentation  = strstr(datascopeDataDesc,"<DSPRESENTATION>");
  dsnumbulkreads  = strstr(datascopeDataDesc,"<DSNUMBULKREADS>");
  dsfilename   = strstr(datascopeDataDesc,"<DSFILENAME>");


  if (dsTable != NULL) {
    *dsTable = '\0';
    dsTable += 9;
    if ((tmpPtr  =  strstr(dsTable,"</DSTABLE>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dsTable: %s\n",dsTable);
/*      return(INP_ERR_RES_FORMAT);*/
    }
    else
	*tmpPtr = '\0';
    if ((datascopeSI->dstable  =strdup(dsTable)) == NULL)
      return MEMORY_ALLOCATION_ERROR;
  }
  else 
    datascopeSI->dstable = NULL;

  if (dsFind != NULL) {
    *dsFind = '\0';
    dsFind += 8;
    if ((tmpPtr  =  strstr(dsFind,"</DSFIND>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dsFind: %s\n",dsFind);
/*      return(INP_ERR_RES_FORMAT);*/
    }
    else
	*tmpPtr = '\0';
    if ((datascopeSI->dsfind  =strdup(dsFind)) == NULL)
      return MEMORY_ALLOCATION_ERROR;
  }
  else 
    datascopeSI->dsfind = NULL;

  if (dsFindRev != NULL) {
      *dsFindRev = '\0';
      dsFindRev += 11;
      if ((tmpPtr  =  strstr(dsFindRev,"</DSFINDREV>")) == NULL) {
	  fprintf(stdout, "getStateInfo:  Error in dsFindRev: %s\n",dsFindRev);
/*  	  return(INP_ERR_RES_FORMAT);*/
      }
      else
	  *tmpPtr = '\0';
      if ((datascopeSI->dsfindRev  =strdup(dsFindRev)) == NULL)
	  return MEMORY_ALLOCATION_ERROR;
  }
  else
      datascopeSI->dsfindRev = NULL;


  if (dsProcess != NULL) {
    *dsProcess = '\0';
    dsProcess += 11;
    if ((tmpPtr  =  strstr(dsProcess,"</DSPROCESS>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dsProcess: %s\n",dsProcess);
/*      return(INP_ERR_RES_FORMAT);*/
    }
    else
	*tmpPtr = '\0';
    datascopeSI->dsprocessStmt = newtbl( 0 );
    while ((tmpPtr  =  strstr(dsProcess,";;")) != NULL) {
      *tmpPtr = '\0';
      strtrim(dsProcess);
      pushtbl( datascopeSI->dsprocessStmt,strdup(dsProcess) );
      dsProcess = tmpPtr + 2;
    }
    strtrim(dsProcess);
    pushtbl( datascopeSI->dsprocessStmt,strdup(dsProcess) );
  }
  else 
    datascopeSI->dsprocessStmt = NULL;

  if (dsposition != NULL) {
    *dsposition = '\0';
    dsposition += 12;
    if ((tmpPtr  =  strstr(dsposition,"</DSPOSITION>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dsposition: %s\n",dsposition);
/*      return(INP_ERR_RES_FORMAT);*/
    }
    else
	*tmpPtr = '\0';
    if ((datascopeSI->position  =strdup(dsposition)) == NULL)
      return MEMORY_ALLOCATION_ERROR;
  }
  else 
    datascopeSI->position = NULL;


  if (dstimeout != NULL) {
    *dstimeout = '\0';
    dstimeout += 11;
    if ((tmpPtr  =  strstr(dstimeout,"</DSTIMEOUT>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dstimeout: %s\n",dstimeout);
/*      return(INP_ERR_RES_FORMAT); */
    }
    else
	*tmpPtr = '\0';
    datascopeSI->timeout = atoi(dstimeout);
  }
  else 
    datascopeSI->timeout = -1;


  if (dsnumofpkts != NULL) {
    *dsnumofpkts = '\0';
    dsnumofpkts += 13;
    if ((tmpPtr  =  strstr(dsnumofpkts,"</DSNUMOFPKTS>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dsnumofpkts: %s\n",dsnumofpkts);
/*      return(INP_ERR_RES_FORMAT); */
    }
    else
	*tmpPtr = '\0';
    datascopeSI->numofpkts  =atoi(dsnumofpkts);
  }
  else 
    datascopeSI->numofpkts = -1;


  if (dspresentation != NULL) {
    *dspresentation = '\0';
    dspresentation += 16;
    if ((tmpPtr  =  strstr(dspresentation,"</DSPRESENTATION>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dspresentation: %s\n",dspresentation);
/*      return(INP_ERR_RES_FORMAT);*/
    }
    else
	*tmpPtr = '\0';
    if ((datascopeSI->presentation  =strdup(dspresentation)) == NULL)
      return MEMORY_ALLOCATION_ERROR;
  }
  else 
    datascopeSI->presentation = NULL;


  if (dsnumbulkreads != NULL) {
    *dsnumbulkreads = '\0';
    dsnumbulkreads += 16;
    if ((tmpPtr  =  strstr(dsnumbulkreads,"</DSNUMBULKREADS>")) == NULL) {
      fprintf(stdout, "getStateInfo:  Error in dsnumbulkreads: %s\n",dsnumbulkreads);
/*      return(INP_ERR_RES_FORMAT); */
    }
    else
	*tmpPtr = '\0';
    datascopeSI->numbulkreads  = atoi(dsnumbulkreads);
  }
  else 
    datascopeSI->numbulkreads = 1;

  if (dsfilename  != NULL) {
      *dsfilename = '\0';
      dsfilename += 12;
      if ((tmpPtr  =  strstr(dsfilename,"</DSFILENAME>")) == NULL) {
	  fprintf(stdout, "getStateInfo:  Error in dsfilename: %s\n",dsfilename);
/*	  return(INP_ERR_RES_FORMAT); */
      }
      else
	  *tmpPtr = '\0';
    if((datascopeSI->tmpFileName = strdup(dsfilename)) == NULL)
      return MEMORY_ALLOCATION_ERROR;
  }
  else
      datascopeSI->tmpFileName = NULL;

  datascopeSI->firstRead = 1;
  datascopeSI->datascopeFlags = datascopeFlags;
  datascopeSI->datascopeMode = datascopeMode;
  if ((datascopeSI->userName  = strdup(userName)) == NULL)
    return MEMORY_ALLOCATION_ERROR; 
  if ((datascopeSI->rsrcInfo = strdup(rsrcInfo)) == NULL)
    return MEMORY_ALLOCATION_ERROR; 
  return MDAS_SUCCESS;

}

int
datascopeSpresGeneric(int first, int last,char *srcname,double vorbtime, int pktid,
		int nbytes, char *vorbpacket, char *buffer)
{
  int i;

  if (last == 0) return (last);
  sprintf(buffer,"%s||%s\n",srcname,vorbpacket);
  i = strlen(buffer);
  return (i);
}

int
getDatascopeTableRowFromXML( char *tableName,
			     char *attrName[MAX_TABLE_COLS],
			     char *attrVal[MAX_TABLE_COLS], 
			     char **mybuffer,
			     int  length, 
			     char *schemaName)
{

  return(0);
}

int
getDatascopeTableRowFromTxt(char *tableName, 
			    char **mybuffer,
			    int  length)

{
  int i,j;
  char *tmpPtr, *tmpPtr1;

  tmpPtr = *mybuffer;

  while (*tmpPtr != '\n'  && *tmpPtr != '\f' && *tmpPtr != '\r') {
    tmpPtr++;
    length--;
    if (length == 0) {
      *mybuffer = tmpPtr;
      return (0);
    }
  }

  *tmpPtr == '\0';
  tmpPtr++;
  length--;
  while (*tmpPtr == '\n'  || *tmpPtr == '\f' || *tmpPtr != '\r' ) {
    tmpPtr++;
    length--;
    if (length == 0) {
      *mybuffer = tmpPtr;
      return (0); 
    }   
  }
  *mybuffer = tmpPtr;
  return (0); 
}

