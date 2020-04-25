FROM python AS dist
WORKDIR /root/project
COPY . .
RUN python setup.py bdist_wheel

FROM scratch
COPY --from=dist /root/project/dist/*.whl .
