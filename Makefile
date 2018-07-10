
NOW_DATE=$(shell date +"%Y-%m-%d")
NOW=$(shell date +"%Y-%m-%d_%H.%M.%S%z")

all: git docker-build

git:
	git submodule update --init --remote
	git submodule foreach git clean -f -d -x
	git submodule foreach git reset --hard HEAD

docker-dependencies: docker-dependencies-build docker-dependencies-push

docker-dependencies-build:
	cd dependencies && time sudo docker build --pull --no-cache -t mbdevpl/transpyle-flash:dependencies-${NOW_DATE} .
	sudo docker tag mbdevpl/transpyle-flash:dependencies-{${NOW_DATE},latest}

docker-dependencies-push:
	sudo docker push mbdevpl/transpyle-flash:dependencies-${NOW_DATE}
	sudo docker push mbdevpl/transpyle-flash:dependencies-latest

docker: docker-build docker-push

docker-build:
	time sudo docker build --pull --no-cache -t mbdevpl/transpyle-flash:build-${NOW_DATE} .
	sudo docker tag mbdevpl/transpyle-flash:{build-${NOW_DATE},latest}

docker-push:
	sudo docker push mbdevpl/transpyle-flash:build-${NOW_DATE}
	sudo docker push mbdevpl/transpyle-flash:latest

docker-run:
	mkdir -p /tmp/docker
	sudo docker run --mount src=/tmp/docker,target=/tmp/docker,type=bind -h transmachine -it mbdevpl/transpyle-flash:latest

basic:
	cd ~/Projects/flash-subset/FLASH4.4
	./setup Sod -auto -2d +Mode3 -site spack
	cd object
	make
	mpirun -np 1 ./flash4

test:
	ROOT_PATH="/tmp/docker/${NOW}"
	mkdir -p ${ROOT_PATH}
	python3 -m unittest --verbose 1> ${ROOT_PATH}/stdout.log 2> ${ROOT_PATH}/stderr.log
	cp -r test_flash.F* ${ROOT_PATH}/
	rm -rf test_flash.F*
