# set base image 
FROM python:3.6

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory

# install dependencies
RUN pip install -r requirements.txt

EXPOSE 8080

# copy the content of the local src directory to the working directory
COPY /. /.

# command to run on container start
CMD [ "python", "." ]