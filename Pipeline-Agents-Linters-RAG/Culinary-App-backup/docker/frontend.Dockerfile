FROM node:14-slim
WORKDIR /app
COPY . /app
RUN npm install -g http-server
EXPOSE 80
CMD ["http-server", "-p", "80"]