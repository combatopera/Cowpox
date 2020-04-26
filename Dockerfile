FROM python AS base
WORKDIR /root/project

FROM base
RUN pip install pyflakes
COPY . .
RUN find -name '*.py' \
    -not -wholename './testapps/*' \
    -not -wholename ./pythonforandroid/recipes/android/src/android/__init__.py \
    -exec pyflakes '{}' +

FROM base as dist
COPY . .
RUN python setup.py bdist_wheel

FROM scratch
COPY --from=dist /root/project/dist/*.whl .
